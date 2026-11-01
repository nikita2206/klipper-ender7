# Ender 6/7 T5L display

Some Ender 6/7 screens have a DWIN **T5L** chip instead of the T5UID1 that
DGUS Reloaded was made for (tested: an Ender 7 screen with sticker
`CXSW043_004`, 480x272). Klipper's side, the `[t5uid1]` module, works
unchanged: both chips speak the same serial protocol. The screen files
don't: T5L screens need a different CFG file, JPEG picture libraries
instead of BMP pages and `.ico` icons, and a touch file without T5UID1's
sound bits. `scripts/t5l_screen/` builds those from DGUS Reloaded for
Klipper 1.0.2 (landscape), and `[t5l_flash]` writes them into the screen
over the printer's USB, so after the first install no SD card is needed.

To tell which chip you have, read the marking on the screen board's main
chip. The rest of the setup (Klipper, MCU firmware with the screen serial
port, `[t5uid1]`) is the same as in the
[DGUS display guide](Ender_6_7_DGUS_Display.md).

## Files

Built files are attached to the fork's GitHub releases (`t5l-screen-*`), or
build them (Python 3 with Pillow; the inputs are downloaded once and
checked against fixed SHA-256 sums):

```
python3 scripts/t5l_screen/build.py OUT [--power-off]
```

`OUT/DWIN_SET/` then holds:

| Slot | File | |
|---|---|---|
| 0-11 | `0_DWIN_ASC.HZK` | font (from the T5UID1 release) |
| 13 | `13_touch.bin` | touch areas (converted) |
| 14 | `14_variable.bin` | values shown on pages (icon library 37 moved to 44) |
| 22 | `22_config.bin` | initial values |
| 24, 27, 30-31 | `24_icons.icl`, `27_buttons.icl`, `30_progress_left.icl` | |
| 32-39 | `32_screens.icl` | pages |
| 44-45 | `44_progress_right.icl` | |
|  | `T5LCFG_480272.CFG` | screen settings: landscape, no touch beep, no dimming, pages at slot 32 |

The screen's 16 MB flash has 64 slots of 256 KiB; a file's name starts
with its slot. The CFG comes from the CR-6 T5L port
([Thinkersbluff](https://github.com/Thinkersbluff/DGUS-Reloaded_for_CR6-DWIN-SET_Component))
with byte `0x05` = `0x30` and `0x08` = 32. It is not stored in the 16 MB
flash and can only be changed from an SD card.

`--power-off` adds a "Power off" tile on Settings page 2 with a
confirmation popup (see [Power off tile](#power-off-tile)).

## First install (SD card)

The screen has its own SD slot (on the Ender 7: inside the printer's side;
turn the printer to reach it). Use a card formatted FAT32 with 4096-byte
clusters, with the `DWIN_SET` folder at its root.
Power on with the card in: the screen shows a blue download screen and is
done when it stops changing (seconds for the CFG alone, a few minutes for
everything). Power off and take the card out; with it in, the screen
downloads again at every power-on.

## Updates over USB

Add to printer.cfg (next to `[t5uid1]`):

```
[t5l_flash]
```

Then, with the printer on, Klipper ready and no print running:

```
scripts/t5l_screen/upload.sh -m http://PRINTER_HOST:7125 -p POWER_DEVICE OUT/DWIN_SET 13_touch.bin 32_screens.icl
```

It uploads the files through Moonraker (into `gcodes/t5l_screen/`, removed
afterwards; needs `[virtual_sdcard]`) and runs `SCREEN_FLASH` for each.
Without file names it writes every `<slot>_*` file. `-p` names the
printer's Moonraker power device and power-cycles it at the end; without
it, power-cycle by hand: the screen loads new files at power-on. Then it
reads the current page: `0001` (home) means the screen runs.

It takes about 6 s per 32 KiB: the touch and variable files seconds, the
pages 6 minutes, the font 10 minutes. Upload only what changed.

What `SCREEN_FLASH FILE=<path> SLOT=<n>` does: switches the screen to page
0 and holds it there, fills a 32 KiB buffer in screen RAM (VP `0x8000`)
with 48-byte writes, sets register `0x00AA` = `5A 02 <block> 8000 0020
0000 0000` (write that buffer to flash block `slot*8+n`) and waits for the
screen to clear the `5A`. Blocks in slots 16-31 are read back and compared.

Other commands:

- `SCREEN_READ ADDR=<vp> [LEN=<words>]`: `0x0014` current page, `0x0084`
  page switch request (`5A01 00NN`; the `5A` stays while the screen isn't
  processing requests), `0x0080` live config (`0014 0330` = landscape),
  `0x000F` version.
- `SCREEN_WRITE ADDR=<vp> DATA=<hex>`: `ADDR=0x0084 DATA=5a010012` shows
  page 18; `ADDR=0x0080 DATA=5a140330` sets landscape until power-off.
- `SCREEN_FLASH_READ SLOT=<16-31> [WORD=<offset>] [LEN=<words>]`.
- `SCREEN_HOLD ENABLE=1|0`: stops/allows the t5uid1 module's own page
  switches.

The registers are documented in DWIN's "T5L_DGUSII Application
Development Guide".

## Power off tile

Built with `--power-off`, the tile's popup sends 1 (Yes) to VP `0x2031`.
To power the printer off through a Moonraker power device (here
`printer`), add:

```
[t5uid1_var power_off]
type: input
address: 0x2031
data_type: uint16
script:
  {% if data == printer.t5uid1.constants.popup_confirmed %}
    POWER_OFF_PRINTER
  {% endif %}
run_as_gcode: true

[gcode_macro POWER_OFF_PRINTER]
description: Heaters off, wait for the hotend to cool, then switch the printer off
gcode:
  {% if printer.print_stats.state in ["printing", "paused"] %}
    RESPOND TYPE=error MSG="Not powering off: a print is running"
  {% else %}
    TURN_OFF_HEATERS
    M84
    # The hotend fan runs only while the printer has power: cutting power with
    # a hot nozzle lets heat creep up into the cold end and clog it
    {% if printer.extruder.temperature > 50 %}
      RESPOND MSG="Waiting for the hotend to cool below 50 C before powering off"
      TEMPERATURE_WAIT SENSOR=extruder MAXIMUM=50
    {% endif %}
    _POWER_OFF_NOW
  {% endif %}

# Separate macro: a template's remote calls run while it is rendered, i.e.
# before any of its G-code; here that is only after the TEMPERATURE_WAIT above
[gcode_macro _POWER_OFF_NOW]
gcode:
  {action_call_remote_method("set_device_power", device="printer", state="off")}
```

## Pitfalls

- **Picture entries must be 4-byte aligned.** DWIN's tool ends each JPEG
  with 8+ zero bytes and pads the entry (10-byte header + JPEG) to a
  multiple of 4. With an odd length the screen hangs loading that picture:
  page 0 shows, the first page switch freezes it, and it ignores every
  request (page switch, brightness, reset) while still answering reads.
- **Don't write the active picture library while a page with values is
  shown**: a redraw reads the half-written library and hangs the screen.
  `SCREEN_FLASH` moves to page 0 first. A hung screen recovers with a
  power cycle; if Klipper's own page switch at startup hangs it again, use
  `SCREEN_HOLD`.
- Register `0x00AA` read mode is `0x01`, not `0x10` as the guide says, and
  only reaches slots 16-31. Writes reach all 512 blocks.
- Klipper messages are at most 64 bytes: screen writes over ~50 bytes
  break the MCU link and Klipper shuts down.
- T5UID1 touch files keep a sound id in each record's page high byte; the
  T5L reads it as page 2048+.
- Klipper G-code names can't look like `T<digit>...` (`T5_READ` is
  refused), hence `SCREEN_*`.
