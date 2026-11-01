#!/usr/bin/env bash
# Writes T5L screen files (from build.py) into the screen's flash over its
# serial link: uploads them through Moonraker, then runs Klipper's
# SCREEN_FLASH ([t5l_flash]). See docs/Ender_6_7_T5L_Display.md.
#
#   upload.sh [-m MOONRAKER_URL] [-p POWER_DEVICE] DWIN_SET_DIR [FILE...]
#     -m    Moonraker URL (default http://localhost:7125)
#     -p    the printer's Moonraker power device: power-cycle it at the end,
#           the screen loads new files at power-on (without -p: do it by hand)
#     FILE  default: every <slot>_* file in DWIN_SET_DIR (the CFG can't be
#           written this way, only from an SD card)
#
# Needs curl and jq; Klipper ready, no print running, [virtual_sdcard].
# About 6 s per 32 KiB: touch/variable files seconds, pictures 6 min, font 10 min.
#
# This file may be distributed under the terms of the GNU GPLv3 license.
set -euo pipefail
usage='usage: upload.sh [-m MOONRAKER_URL] [-p POWER_DEVICE] DWIN_SET_DIR [FILE...]'
M=http://localhost:7125 power=
while getopts m:p: o; do
  case $o in m) M=$OPTARG ;; p) power=$OPTARG ;; *) echo "$usage"; exit 2 ;; esac
done
shift $((OPTIND - 1))
dir=${1:?$usage}; shift
cd "$dir"
files=("$@")
[ ${#files[@]} -gt 0 ] || mapfile -t files < <(ls | grep -E '^[0-9]+_' | sort -n)
for f in "${files[@]}"; do
  [[ $f =~ ^[0-9]+_ && -f $f ]] || { echo "$f: not a <slot>_<name> file in $dir"; exit 1; }
done
# Upload directory in Moonraker's gcodes root, which is the [virtual_sdcard]
# path that SCREEN_FLASH resolves relative FILE= against
UP=t5l_screen

info() { curl -sf -m 5 "$M/printer/info" | jq -r .result.state; }
state=$(info) || state=unreachable
[ "$state" = ready ] || { echo "Klipper is '$state', needs 'ready' (printer on, screen connected)"; exit 1; }

trap 'curl -s -m 10 -X DELETE "$M/server/files/directory?path=gcodes/$UP&force=true" >/dev/null || true' EXIT
for f in "${files[@]}"; do
  curl -sf -m 120 -F root=gcodes -F path=$UP -F "file=@$f" "$M/server/files/upload" >/dev/null ||
    { echo "$f: upload to $M failed"; exit 1; }
done

gcode() {  # runs G-code, prints its last response; fails on a Klipper error
  local out
  out=$(curl -s -m 1800 -X POST "$M/printer/gcode/script" --data-urlencode "script=$1")
  curl -s -m 5 "$M/server/gcode_store?count=20" |
    jq -r '.result.gcode_store[] | select(.type=="response") | .message' | tail -n 1
  [ "$(jq -r '.result // empty' <<<"$out")" = ok ] || { jq -r '.error.message' <<<"$out"; return 1; }
}
for f in "${files[@]}"; do
  echo "== $f -> slot ${f%%_*}"
  gcode "SCREEN_FLASH FILE=$UP/$f SLOT=${f%%_*}"
done

if [ -z "$power" ]; then
  echo "== done: power-cycle the printer, the screen loads new files at power-on"
  exit 0
fi
echo "== power-cycling '$power'"
curl -sf -m 10 -X POST "$M/machine/device_power/device?device=$power&action=off" >/dev/null
sleep 8
curl -sf -m 10 -X POST "$M/machine/device_power/device?device=$power&action=on" >/dev/null
for _ in $(seq 60); do [ "$(info || true)" = ready ] && break; sleep 2; done
[ "$(info || true)" = ready ] || { echo "Klipper did not get ready after power-on"; exit 1; }
sleep 5
# 0001 (home) = the screen runs; 0000 with Klipper ready = it hung loading a page
echo "current page (0x0014, expect 0001): $(gcode 'SCREEN_READ ADDR=0x0014')"
