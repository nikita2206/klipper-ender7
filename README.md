# Klipper fork for Creality Ender 6/7 DGUS display

This is a fork of [Klipper](https://github.com/Klipper3d/klipper) with
[Desuuuu's DGUS Reloaded](https://github.com/Desuuuu/klipper) patches
applied on top. These patches add support for the DWIN T5UID1 (DGUS)
touchscreen used in Creality Ender 6 and Ender 7 printers, allowing the
stock display to work with Klipper instead of requiring a replacement.

A GitHub Actions workflow opens a pull request merging each new upstream
Klipper release into this fork.

### Fork-specific patches

- **DGUS display support** — Desuuuu's t5uid1 module that drives the stock
  DWIN DGUS touchscreen over serial. Adds MCU-side UART handling (STM32,
  AVR, LPC176X, ATSAMD) and a `[t5uid1]` Klipper config section for
  display control including pages, menus, and touchscreen input. The
  display firmware is included in [`dwin_custom/ender7/`](dwin_custom/ender7/).
- **T5L screens** — some Ender 6/7 screens have the newer DWIN T5L chip.
  [`scripts/t5l_screen/`](scripts/t5l_screen/) builds DGUS Reloaded for it,
  and the `[t5l_flash]` module writes screen files over the printer's USB,
  no SD card needed: [T5L display guide](docs/Ender_6_7_T5L_Display.md).
- **Current Klipper internals** — the display code was re-applied onto
  upstream Klipper in 2026-11 and follows renamed internals (MCU serial
  responses, probe session state, probing progress).

### Installation

See the full [Ender 6/7 DGUS Display setup guide](docs/Ender_6_7_DGUS_Display.md)
for step-by-step instructions covering display firmware flashing, Klipper
installation, configuration, and calibration. Screens with a T5L chip:
[T5L display guide](docs/Ender_6_7_T5L_Display.md).

---

Welcome to the Klipper project!

[![Klipper](docs/img/klipper-logo-small.png)](https://www.klipper3d.org/)

https://www.klipper3d.org/

The Klipper firmware controls 3d-Printers. It combines the power of a
general purpose computer with one or more micro-controllers. See the
[features document](https://www.klipper3d.org/Features.html) for more
information on why you should use the Klipper software.

Start by [installing Klipper software](https://www.klipper3d.org/Installation.html).

Klipper software is Free Software. See the [license](COPYING) or read
the [documentation](https://www.klipper3d.org/Overview.html). We
depend on the generous support from our
[sponsors](https://www.klipper3d.org/Sponsors.html).
