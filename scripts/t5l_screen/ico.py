# Reads T5UID1 .ico icon libraries (the T5L can't use them; build.py
# converts them to ICL).
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import struct, sys
from PIL import Image


def read_ico(path):
    """T5UID1 .ico: 256 KiB index of 8-byte entries (w, h, u32 BE offset in
    16-bit words, pad), RGB565 pixels."""
    b = open(path, 'rb').read()
    icons = {}
    for i in range(0x40000 // 8):
        e = b[i * 8 : i * 8 + 8]
        w, h = e[0], e[1]
        if not w or not h:
            continue
        off = struct.unpack('>I', e[2:6])[0] * 2
        px = b[off : off + w * h * 2]
        img = Image.new('RGB', (w, h))
        img.putdata(
            [
                (
                    (v >> 11 & 31) * 255 // 31,
                    (v >> 5 & 63) * 255 // 63,
                    (v & 31) * 255 // 31,
                )
                for v in struct.unpack('>%dH' % (w * h), px)
            ]
        )
        icons[i] = img
    return icons


if __name__ == '__main__':
    for f in sys.argv[1:]:
        ic = read_ico(f)
        print(
            f,
            len(ic),
            'icons; ids',
            min(ic),
            '..',
            max(ic),
            '; sizes',
            sorted({im.size for im in ic.values()})[:8],
        )
