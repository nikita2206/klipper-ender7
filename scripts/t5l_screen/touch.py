# Parses DWIN touch files (13_touch.bin). Records are 16 bytes, or longer
# for controls with extra data (0xFExx/0xFDxx codes); the file has no length
# fields, so each record's length is the one after which the next one parses.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import struct

PAGES = set(range(0, 256))


def plausible(b, i):
    if i == len(b) or b[i : i + 2] == b'\xff\xff':
        return True
    if i + 16 > len(b):
        return False
    pid, x1, y1, x2, y2, nxt, on, code = struct.unpack('>8H', b[i : i + 16])
    return (
        (pid & 0xFF) in PAGES
        and x1 < x2 <= 0x300
        and y1 < y2 <= 0x300
        and (code >> 8) in (0x00, 0xFE, 0xFD, 0xFF)
    )


def parse(b):
    """Returns [(offset, length, pid, code)]; length chosen so the next
    record is plausible."""
    recs, i = [], 0
    while i < len(b) and b[i : i + 2] != b'\xff\xff':
        code = struct.unpack('>H', b[i + 14 : i + 16])[0]
        for L in (16,) if code >> 8 not in (0xFE, 0xFD) else (32, 48, 64, 16):
            if plausible(b, i + L):
                break
        else:
            raise ValueError(f'cannot size record at {i} code {code:#x}')
        recs.append((i, L, struct.unpack('>H', b[i : i + 2])[0], code))
        i += L
    return recs, i
