# Writes files into the DWIN T5L touchscreen's 16 MB flash over the screen's
# serial link (the t5uid1 module), so screen builds need no SD card.
# See docs/Ender_6_7_T5L_Display.md and scripts/t5l_screen/.
#
# G-code:
#   SCREEN_FLASH FILE=<path> SLOT=<0-63>  write a file at slot*256 KiB; a
#                relative path is inside [virtual_sdcard] (Moonraker uploads)
#   SCREEN_FLASH_READ SLOT=<16-31> [WORD=<offset>] [LEN=<words>]
#   SCREEN_READ ADDR=<vp> [LEN=<words>]   SCREEN_WRITE ADDR=<vp> DATA=<hex>
#   SCREEN_HOLD ENABLE=0|1   drop the t5uid1 module's own page switches
#
# Copyright (C) 2026  Nikita Nefedov
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import logging, os, sys

BUF_VP = 0x8000      # 32 KiB staging buffer in screen RAM (VP 0x8000-0xBFFF)
READ_VP = 0xC000     # where SCREEN_FLASH_READ puts flash data
BLOCK = 0x8000       # the screen writes flash in 32 KiB blocks (reg 0x00AA)
# Klipper messages are at most 64 bytes including framing; t5uid1_write adds
# ~11 (header, ids, length, VP address). 60-byte chunks broke the MCU link.
CHUNK = 48
# A 54-byte frame takes 4.7 ms at the screen's 115200 baud; the board's screen
# send buffer is 96 bytes and drops whole frames when full.
PACE = 0.008
REG_PAGE, REG_CUR_PAGE, REG_FLASH = 0x0084, 0x0014, 0x00AA


class T5LFlash:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()
        self.replies = {}
        self.hold = False
        self.t5 = None
        gcode = self.printer.lookup_object('gcode')
        for name, fn in (('SCREEN_FLASH', self.cmd_flash),
                         ('SCREEN_FLASH_READ', self.cmd_flash_read),
                         ('SCREEN_READ', self.cmd_read),
                         ('SCREEN_WRITE', self.cmd_write),
                         ('SCREEN_HOLD', self.cmd_hold)):
            gcode.register_command(name, fn)
        self.printer.register_event_handler('klippy:connect', self._connect)

    def _connect(self):
        t5 = self.t5 = self.printer.lookup_object('t5uid1')
        self.t5mod = sys.modules[type(t5).__module__]
        switch_page, handle_received = t5.switch_page, t5.handle_received

        # Hold: while uploading, the screen must not load another page. A
        # redraw reading a half-written picture library froze it (2026-11-01).
        def held_switch_page(name, send=True):
            if send and self.hold:
                logging.info('t5l_flash: hold, dropped switch_page(%s)', name)
                return
            return switch_page(name, send=send)

        # t5uid1 only handles the reads it asked for; keep every reply so the
        # commands below can wait for theirs
        def keep_reply(address, data):
            self.replies[address] = bytes(data)
            return handle_received(address, data)
        t5.switch_page, t5.handle_received = held_switch_page, keep_reply

    def _error(self, msg):
        return self.printer.command_error(msg)

    def _read(self, addr, words, timeout=2.0):
        self.replies.pop(addr, None)
        self.t5.t5uid1_command_read(addr, words)
        end = self.reactor.monotonic() + timeout
        while addr not in self.replies:
            if self.reactor.monotonic() > end:
                raise self._error('screen: no reply reading %#06x' % addr)
            self.reactor.pause(self.reactor.monotonic() + 0.02)
        return self.replies[addr]

    def _wait_done(self, addr, timeout=10.0):
        # system registers start with 0x5A as "request"; the screen clears it
        # when done. A screen whose main loop hangs never clears it.
        end = self.reactor.monotonic() + timeout
        while self._read(addr, 1)[0] != 0:
            if self.reactor.monotonic() > end:
                raise self._error('screen did not process %#06x (hung?'
                                  ' power-cycle the printer)' % addr)
            self.reactor.pause(self.reactor.monotonic() + 0.05)

    def _request(self, addr, data):
        self.t5.t5uid1_command_write(addr, bytearray(data))
        self._wait_done(addr)

    def _fill_buffer(self, data):
        old = self.t5mod.CMD_DELAY   # t5uid1 paces all writes by this
        self.t5mod.CMD_DELAY = PACE
        try:
            for i in range(0, len(data), CHUNK):
                self.t5.t5uid1_command_write(BUF_VP + i // 2,
                                             bytearray(data[i:i + CHUNK]))
                if i % (CHUNK * 50) == 0:   # keep Klipper's send queue short
                    self.reactor.pause(self.reactor.monotonic() + 0.3)
        finally:
            self.t5mod.CMD_DELAY = old

    def _flash_read(self, slot, word, words):
        # read mode 0x01: the guide says 0x10, this screen only does 0x01;
        # it only reaches slots 16-31 (other slots read as zeros)
        self._request(REG_FLASH, [0x5A, 0x01, slot, word >> 16 & 0xFF,
                                  word >> 8 & 0xFF, word & 0xFF,
                                  READ_VP >> 8, READ_VP & 0xFF,
                                  words >> 8, words & 0xFF, 0, 0])
        return self._read(READ_VP, words)

    def _check_ready(self):
        if self.t5 is None or not self.t5._is_connected:
            raise self._error('screen not connected')
        state = self.printer.lookup_object('print_stats').get_status(
            self.reactor.monotonic())['state']
        if state in ('printing', 'paused'):
            raise self._error('not while a print is running')

    def cmd_flash(self, gcmd):
        self._check_ready()
        path = gcmd.get('FILE')
        slot = gcmd.get_int('SLOT', minval=0, maxval=63)
        if not os.path.isabs(path):
            sdcard = self.printer.lookup_object('virtual_sdcard', None)
            if sdcard is None:
                raise self._error('relative FILE needs [virtual_sdcard]')
            path = os.path.join(sdcard.sdcard_dirname, path)
        # anything but a command error here would shut Klipper down
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except IOError as e:
            raise self._error('cannot read %s: %s' % (path, e))
        blocks = -(-len(data) // BLOCK)
        if slot * 8 + blocks > 512:
            raise self._error('%s does not fit at slot %d' % (path, slot))
        # page 0 has no variables, so nothing is redrawn during the upload
        self.hold = True
        self._request(REG_PAGE, [0x5A, 0x01, 0x00, 0x00])
        name = path.rsplit('/', 1)[-1]
        t0 = self.reactor.monotonic()
        for b in range(blocks):
            chunk = data[b * BLOCK:(b + 1) * BLOCK]
            chunk += b'\x00' * (BLOCK - len(chunk))
            self._fill_buffer(chunk)
            blk = slot * 8 + b
            # D11 0x5A request, D10 0x02 write 32 KiB, D9:D8 block, D7:D6
            # source VP, D5:D4 settle delay (32 ms) after the write
            self._request(REG_FLASH, [0x5A, 0x02, blk >> 8, blk & 0xFF,
                                      BUF_VP >> 8, BUF_VP & 0xFF,
                                      0x00, 0x20, 0, 0, 0, 0])
            if 16 <= slot + b // 8 <= 31:
                word = (b % 8) * BLOCK // 2
                got = self._flash_read(slot + b // 8, word, 8)
                if got != chunk[:16]:
                    raise self._error('%s block %d: read back %s, expected %s'
                                      % (name, b, got.hex(), chunk[:16].hex()))
            if b % 8 == 7 or b == blocks - 1:
                gcmd.respond_info('%s: %d/%d blocks, %.0fs' % (
                    name, b + 1, blocks, self.reactor.monotonic() - t0))
        gcmd.respond_info('%s written at slot %d. The screen loads new files at'
                          ' power-on: power-cycle the printer.' % (name, slot))

    def cmd_flash_read(self, gcmd):
        self._check_ready()
        slot = gcmd.get_int('SLOT', minval=16, maxval=31)
        word = int(gcmd.get('WORD', '0'), 0)
        words = gcmd.get_int('LEN', 8, minval=1, maxval=32)
        gcmd.respond_info('slot %d word %#x: %s' % (
            slot, word, self._flash_read(slot, word, words).hex()))

    def cmd_read(self, gcmd):
        if self.t5 is None:
            raise self._error('screen not connected')
        addr = int(gcmd.get('ADDR'), 0)
        words = gcmd.get_int('LEN', 1, minval=1, maxval=32)
        gcmd.respond_info('%#06x=%s' % (addr, self._read(addr, words).hex()))

    def cmd_write(self, gcmd):
        if self.t5 is None:
            raise self._error('screen not connected')
        addr = int(gcmd.get('ADDR'), 0)
        data = bytearray.fromhex(gcmd.get('DATA'))
        if len(data) > CHUNK or len(data) % 2:
            raise self._error('DATA must be 2-%d bytes, an even count' % CHUNK)
        self.t5.t5uid1_command_write(addr, data)
        gcmd.respond_info('wrote %#06x=%s' % (addr, data.hex()))

    def cmd_hold(self, gcmd):
        self.hold = bool(gcmd.get_int('ENABLE', 1))
        gcmd.respond_info('screen hold %s' % ('on' if self.hold else 'off'))


def load_config(config):
    return T5LFlash(config)
