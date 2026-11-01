# DWIN ICL picture libraries (DGUS_3 format, JPEG entries) as the T5L reads
# them, written byte-compatible with DWIN's own tool.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
import io, struct
from PIL import Image

# every DWIN-made JPEG has this fixed header (APP0, 2x DQT, SOF0, 4x DHT, SOS)
JPEG_HEADER_LEN = 626


def crc16_modbus(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def jpeg(img):
    """Encode like the DGUS tool: baseline, 4:2:0, all-1 quant tables, standard
    Huffman, 120 dpi, and a 15-byte SOS padded with 3x 0xFF so the scan data
    starts at the fixed offset 626 that DWIN's files use."""
    out = io.BytesIO()
    img.convert('RGB').save(
        out,
        'JPEG',
        quality=100,
        subsampling=2,
        optimize=False,
        progressive=False,
        dpi=(120, 120),
    )
    j = out.getvalue()
    sos = j.find(b'\xff\xda\x00\x0c')
    assert sos == JPEG_HEADER_LEN - 17, 'unexpected JPEG header layout'
    j = (
        j[:sos]
        + b'\xff\xda\x00\x0f'
        + j[sos + 4 : sos + 14]
        + b'\xff\xff\xff'
        + j[sos + 14 :]
    )
    # DWIN's tool ends every JPEG with 8+ zero bytes and pads the entry
    # (10-byte header + JPEG) to a multiple of 4. The T5L hangs loading a
    # picture whose entry length is odd (tested: picture 1 froze the screen,
    # picture 0 didn't).
    j += b'\x00' * 8
    return j + b'\x00' * (-(10 + len(j)) % 4)


def write_icl(entries):
    """entries: {id: (w, h, jpeg_bytes)} -> ICL bytes (DGUS_3 format)."""
    max_id = max(entries)
    table_end = 16 + 4 * (max_id + 1)
    offs, blobs, pos = [], [], table_end
    for i in range(max_id + 1):
        if i in entries:
            w, h, j = entries[i]
            blob = (
                struct.pack(
                    '>HHHI', w, h, JPEG_HEADER_LEN, len(j) - JPEG_HEADER_LEN
                )
                + j
            )
            offs.append(pos)
            blobs.append(blob)
            pos += len(blob)
        else:
            offs.append(0)
    body = (
        struct.pack('>I', 0)
        + b'\x04'
        + struct.pack('>H', max_id)
        + b'\x00'
        + b''.join(struct.pack('>I', o) for o in offs)
        + b''.join(blobs)
    )
    body = (
        struct.pack('>I', len(body) - 4 + 4) + body[4:]
    )  # length field = file size - 8
    return b'DGUS_3' + struct.pack('<H', crc16_modbus(body)) + body


def read_icl(b):
    max_id = struct.unpack('>H', b[13:15])[0]
    out = {}
    for i in range(max_id + 1):
        o = struct.unpack('>I', b[16 + 4 * i : 20 + 4 * i])[0]
        if o:
            w, h, a, c = struct.unpack('>HHHI', b[o : o + 10])
            out[i] = (w, h, b[o + 10 : o + 10 + a + c])
    return out
