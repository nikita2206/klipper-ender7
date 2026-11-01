#!/usr/bin/env python3
"""Builds DGUS Reloaded for Klipper 1.0.2 (made for the DWIN T5UID1 chip) for
the Ender 6/7 screens with a DWIN T5L chip, landscape 480x272.
See docs/Ender_6_7_T5L_Display.md.

usage: build.py OUT_DIR [--power-off]
  needs Pillow; downloads its inputs once
  --power-off  add a "Power off" tile on Settings page 2 (needs printer.cfg
               setup, see the doc)
Writes OUT_DIR/DWIN_SET/<slot>_<name>: the number is the flash slot
(256 KiB each) the file goes to, for upload.sh as for the SD card.

This file may be distributed under the terms of the GNU GPLv3 license.
"""

import glob, hashlib, io, math, os, re, shutil, sys, tarfile, tempfile
import zipfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageChops, ImageStat
from icl import jpeg, write_icl, read_icl
from ico import read_ico
from feature import power_tile, popup, touch_file, POPUP_PAGE, POPUP_SEL_PAGE

INPUTS = {  # name: (url, sha256)
    'dgus-reloaded-klipper-1.0.2.tar.gz': (
        'https://github.com/Desuuuu/DGUS-reloaded-Klipper/releases/download/'
        '1.0.2/DWIN_SET.tar.gz',
        '3e10f12bc1c08340eb39984a38f5179ea792214c8408e29eeea529aab9460c5f',
    ),
    # CR-6 T5L port: only its CFG is used (the screen's hardware settings)
    'cr6-dwin-set-2.0.3.zip': (
        'https://github.com/Thinkersbluff/'
        'DGUS-Reloaded_for_CR6-DWIN-SET_Component/releases/download/'
        'v2.0.3/DWIN_SET_V.2.0.3.zip',
        '12f69eec9ac23df6f0f81d7a8bc5696892eacb164bc691ec4b60b9fb991ae8e0',
    ),
    'Carlito-Regular.ttf': (
        'https://github.com/googlefonts/carlito/raw/main/fonts/ttf/'
        'Carlito-Regular.ttf',
        'f6418f708baede9789daef5d458c0f53d2a888af9820e8062934e504fedc6595',
    ),
}
CACHE = os.path.expanduser('~/.cache/klipper-t5l-screen')
SLOT = 0x40000
# The CFG says where the picture library is (byte 0x08). 32 as in the CR-6
# port's CFG; 2 MB of pictures there fill slots 32-39, so the right progress
# bar icons move from 37 (T5UID1 layout) to 44.
SCREENS, PROGRESS_RIGHT = 32, 44


def fetch(name):
    url, sha = INPUTS[name]
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        os.makedirs(CACHE, exist_ok=True)
        data = urllib.request.urlopen(url).read()
        if hashlib.sha256(data).hexdigest() != sha:
            sys.exit(f'{name}: checksum mismatch for {url}')
        open(path, 'wb').write(data)
    return path


def unpad(j):  # DWIN's padded JPEG back to one Pillow can decode
    end = j.rfind(b'\xff\xd9') + 2
    return j[:609] + b'\xff\xda\x00\x0c' + j[613:623] + j[626:end]


def psnr(imgs, icl_bytes):
    worst = 99.0
    for i, (w, h, j) in read_icl(icl_bytes).items():
        assert (10 + len(j)) % 4 == 0, f'picture {i}: entry not 4-byte aligned'
        dec = Image.open(io.BytesIO(unpad(j))).convert('RGB')
        assert dec.size == imgs[i].size == (w, h), i
        mse = (
            sum(
                v * v
                for v in ImageStat.Stat(
                    ImageChops.difference(dec, imgs[i].convert('RGB'))
                ).rms
            )
            / 3
        )
        worst = min(worst, 99 if mse == 0 else 10 * math.log10(255**2 / mse))
    return worst


def main(out, power_off, src):
    tarfile.open(fetch('dgus-reloaded-klipper-1.0.2.tar.gz')).extractall(
        src, filter='data'
    )
    src = os.path.join(src, 'DWIN_SET')
    cr6_cfg = zipfile.ZipFile(fetch('cr6-dwin-set-2.0.3.zip')).read(
        'DWIN_SET/T5LCFG_272480K.CFG'
    )
    font = fetch('Carlito-Regular.ttf')
    out = os.path.join(out, 'DWIN_SET')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)

    screens = {
        int(re.match(r'(\d+)_', os.path.basename(f)).group(1)): Image.open(
            f
        ).convert('RGB')
        for f in glob.glob(src + '/*.bmp')
    }
    if power_off:
        screens[18] = power_tile(screens[18], font)  # Settings page 2
        screens[POPUP_PAGE] = popup(screens[204], font)
        screens[POPUP_SEL_PAGE] = popup(screens[205], font)
    libs = {f'{SCREENS}_screens.icl': screens}
    for f, slot in (
        ('24_icons', 24),
        ('27_buttons', 27),
        ('30_progress_left', 30),
        ('37_progress_right', PROGRESS_RIGHT),
    ):
        libs[f'{slot}_{f.split("_", 1)[1]}.icl'] = read_ico(f'{src}/{f}.ico')
    for name, imgs in libs.items():
        data = write_icl(
            {i: (im.size[0], im.size[1], jpeg(im)) for i, im in imgs.items()}
        )
        open(f'{out}/{name}', 'wb').write(data)
        print(
            f'{name:24} {len(imgs):3} pictures {len(data):8} B'
            f'  worst PSNR {psnr(imgs, data):.1f} dB'
        )

    open(f'{out}/13_touch.bin', 'wb').write(
        touch_file(open(f'{src}/13_touch.bin', 'rb').read(), power_off)
    )
    var = bytearray(open(f'{src}/14_variable.bin', 'rb').read())
    moved = 0
    for o in range(0x4000, len(var) - 31, 32):
        # icon entries (type 0x00) keep their library slot in byte 20
        if var[o] == 0x5A and var[o + 1] == 0x00 and var[o + 20] == 37:
            var[o + 20] = PROGRESS_RIGHT
            moved += 1
    assert moved == 2, moved
    open(f'{out}/14_variable.bin', 'wb').write(var)
    for f in ('22_config.bin', '0_DWIN_ASC.HZK'):
        shutil.copy(f'{src}/{f}', out)

    cfg = bytearray(cr6_cfg)
    # 0x05 = 0x30: load the 22 file at power-on, touch auto-upload on, no touch
    # beep (volume: 0 in printer.cfg), no standby dimming, 0 degrees (landscape)
    cfg[0x05] = 0x30
    cfg[0x08] = SCREENS  # picture library slot
    open(f'{out}/T5LCFG_480272.CFG', 'wb').write(cfg)

    used = {}
    for f in sorted(os.listdir(out)):
        m = re.match(r'(\d+)_', f)
        if m:
            first = int(m.group(1))
            for s in range(
                first, first - (-os.path.getsize(f'{out}/{f}') // SLOT)
            ):
                assert s not in used and s < 64, (
                    f'slot {s}: {f} overlaps {used.get(s)}'
                )
                used[s] = f
    print(
        'slots:',
        ', '.join(
            f'{f} {min(s for s in used if used[s] == f)}-'
            f'{max(s for s in used if used[s] == f)}'
            for f in sorted(
                set(used.values()), key=lambda f: int(f.split('_')[0])
            )
        ),
    )


if __name__ == '__main__':
    args = sys.argv[1:]
    power_off = '--power-off' in args
    args = [a for a in args if a != '--power-off']
    if len(args) != 1 or args[0].startswith('-'):
        sys.exit(__doc__)
    # per-run source directory, so parallel builds don't share one
    with tempfile.TemporaryDirectory() as src:
        main(args[0], power_off, src)
