# Flashing the DGUS Display Firmware

This guide explains how to flash the DGUS Reloaded firmware onto the
DWIN T5UID1 touchscreen used in Creality Ender 6 and Ender 7 printers.

The firmware files are included in this repository under
[`dwin_custom/ender7/DWIN_SET/`](../dwin_custom/ender7/DWIN_SET/)
(from [DGUS Reloaded v1.0.2](https://github.com/Desuuuu/DGUS-reloaded-Klipper/releases/tag/1.0.2)).

These files are for the T5UID1 chip. Screens with a DWIN T5L chip need
other files and can be updated over USB: see the
[T5L display guide](Ender_6_7_T5L_Display.md).

## Steps

1. Format a micro SD card (**8 GB or smaller**) as **FAT32** with
   **4096 byte** allocation unit size.

2. Copy the entire `DWIN_SET` folder from
   `dwin_custom/ender7/DWIN_SET/` to the **root** of the SD card. The
   card should contain a single folder named `DWIN_SET`.

3. **Power off** the printer completely.

4. Insert the micro SD card into the **touchscreen's** SD card slot
   (on the back of the display, not the mainboard's slot).

5. **Power on** the printer (power only — do not connect USB). The
   screen will turn blue and flashing will begin.

6. Wait until you see `END` at the top of the screen. This takes
   roughly 30–60 seconds.

7. **Power off** the printer and remove the SD card.

## Coming from a different firmware

If your display was previously running a different firmware (e.g. the
stock Creality firmware), you should replace `T5UID1.CFG` in the
`DWIN_SET` folder with the flash-reset version before flashing:

```bash
cp dwin_custom/ender7/flash_reset_T5UID1.CFG dwin_custom/ender7/DWIN_SET/T5UID1.CFG
```

This resets the display's configuration to defaults, avoiding potential
issues from leftover settings.

## Screen rotation

If your display is mounted at a non-standard orientation, replace
`T5UID1.CFG` in the `DWIN_SET` folder with the appropriate rotation
config before flashing:

| Rotation | File |
|----------|------|
| 90°      | `dwin_custom/ender7/T5UID1_90.CFG` |
| 180°     | `dwin_custom/ender7/T5UID1_180.CFG` |
| 270°     | `dwin_custom/ender7/T5UID1_270.CFG` |

## Print status and progress

To get print status on the display, add these to your slicer's G-code:

- **Start G-code:** add `DGUS_PRINT_START` after homing/heating
- **End G-code:** add `DGUS_PRINT_END` at the end

For print progress percentage, your slicer or host needs to send `M73`
commands. In OctoPrint, install the
[M73 Progress](https://plugins.octoprint.org/plugins/m73progress/) plugin.
