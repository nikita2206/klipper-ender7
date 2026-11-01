# Converts the T5UID1 touch file for the T5L and, optionally, adds a
# "Power off" tile (Settings page 2) with a confirmation popup. Yes on the
# popup sends 1 to VP 0x2031; printer.cfg decides what that does.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import struct
from PIL import Image, ImageDraw, ImageFont
from touch import parse

TILE_SRC, TILE_DST = (
    (189, 45, 292, 148),
    (189, 158, 292, 261),
)  # "Save config." tile -> bottom middle
POPUP_PAGE, POPUP_SEL_PAGE, VP_POWER_OFF = 216, 217, 0x2031


def touch_file(src, power_off=False):
    b = bytearray(src)
    recs, end = parse(bytes(b))
    out = bytearray()
    abort = None
    for o, L, pid, code in recs:
        r = bytearray(b[o : o + L])
        # T5UID1 keeps a sound id in the page's high byte; the T5L reads the
        # top 4 bits as sound and 12 bits as page, so 0x08xx would point at
        # page 2048+
        r[0] = 0
        out += r
        if pid & 0xFF == 2 and code == 0xFE01 and abort is None:
            abort = bytearray(r)
    if not power_off:
        return bytes(out) + b'\xff\xff'
    keys = [
        bytearray(b[o : o + L])
        for o, L, pid, code in recs
        if pid & 0xFF == 204
    ]
    # Power off tile: same popup control as "Abort print", own page and
    # return VP
    t = abort
    t[0:2] = struct.pack('>H', 18)
    t[2:10] = struct.pack(
        '>4H', TILE_DST[0], TILE_DST[1], TILE_DST[2] - 1, TILE_DST[3] - 1
    )
    t[0x11:0x13] = struct.pack('>H', VP_POWER_OFF)
    t[0x14:0x16] = struct.pack('>H', POPUP_PAGE)
    out += t
    for k in keys:  # Yes (1) / No (255) areas of the popup page
        k[0:2] = struct.pack('>H', POPUP_PAGE)
        k[0x0C:0x0E] = struct.pack('>H', POPUP_SEL_PAGE)
        out += k
    return bytes(out) + b'\xff\xff'


def _bright_bbox(img, box, thr):
    c = img.crop(box).convert('L')
    px = c.load()
    pts = [
        (x, y)
        for x in range(c.width)
        for y in range(c.height)
        if px[x, y] > thr
    ]
    return (
        box[0] + min(p[0] for p in pts),
        box[1] + min(p[1] for p in pts),
        box[0] + max(p[0] for p in pts) + 1,
        box[1] + max(p[1] for p in pts) + 1,
    )


def power_tile(page, font):
    page = page.copy()
    d = ImageDraw.Draw(page)
    tile = page.crop(TILE_SRC)
    bg = tile.getpixel((6, 6))
    fg = max(tile.crop((8, 81, 93, 96)).get_flattened_data(), key=sum)
    page.paste(tile, TILE_DST[:2])
    x0, y0 = TILE_DST[:2]
    d.rectangle((x0 + 3, y0 + 3, x0 + 99, y0 + 99), fill=bg)
    # power symbol: open circle + bar, sized like the other tile icons
    cx, cy, r, w = x0 + 51, y0 + 42, 19, 3
    d.arc(
        (cx - r, cy - r, cx + r, cy + r), start=-55, end=235, fill=fg, width=w
    )
    d.line((cx, cy - r - 4, cx, cy + 1), fill=fg, width=w)
    f = ImageFont.truetype(font, 18)
    tw = d.textlength('Power off', font=f)
    d.text((x0 + 51 - tw / 2, y0 + 77), 'Power off', font=f, fill=fg)
    return page


def popup(img, font):
    img = img.copy()
    d = ImageDraw.Draw(img)
    bb = _bright_bbox(img, (125, 105, 355, 155), 120)  # "Abort print?" title
    bg = img.getpixel((bb[0] - 4, bb[1] - 4))
    fg = max(img.crop(bb).get_flattened_data(), key=sum)
    d.rectangle((bb[0] - 2, bb[1] - 2, bb[2] + 2, bb[3] + 2), fill=bg)
    f = ImageFont.truetype(font, 18)
    text = 'Power off printer?'
    tw = d.textlength(text, font=f)
    cx = (bb[0] + bb[2]) / 2
    d.text((cx - tw / 2, bb[3] - 18 + 3), text, font=f, fill=fg, anchor=None)
    return img
