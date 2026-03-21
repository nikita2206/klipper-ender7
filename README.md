# Klipper fork for Creality Ender 6/7 DGUS display

This is a fork of [Klipper](https://github.com/Klipper3d/klipper) with
[Desuuuu's DGUS Reloaded](https://github.com/Desuuuu/klipper) patches
applied on top. These patches add support for the DWIN T5UID1 (DGUS)
touchscreen used in Creality Ender 6 and Ender 7 printers, allowing the
stock display to work with Klipper instead of requiring a replacement.

A GitHub Actions workflow keeps this fork up to date with upstream Klipper
releases automatically.

### Fork-specific patches

- **DGUS display support** — Desuuuu's t5uid1 module that drives the stock
  DWIN DGUS touchscreen over serial. Adds MCU-side UART handling (STM32,
  AVR, LPC176X, ATSAMD) and a `[t5uid1]` Klipper config section for
  display control including pages, menus, and touchscreen input.
- **Probe compatibility fix** — updates the t5uid1 code to use the current
  Klipper probe API (`self.probe.multi != "OFF"`) instead of the removed
  `multi_probe_pending` attribute, preventing crashes during bed mesh
  probing with the display active.

### Installation

You will need to flash custom firmware onto the display first. See the
[DGUS Reloaded wiki](https://github.com/Desuuuu/DGUS-reloaded-Klipper/wiki/Flashing-the-firmware)
and [firmware releases](https://github.com/Desuuuu/DGUS-reloaded-Klipper/releases).

Then install Klipper from this repo instead of the upstream one — for
example, after installing Klipper via [KIAUH](https://github.com/dw-0/kiauh):

```bash
cd ~
rm -rf klipper
git clone https://github.com/nikita2206/klipper-ender7.git klipper
```

Add the following to your `printer.cfg` to enable the display:

```ini
[t5uid1]
firmware: dgus_reloaded
machine_name: Ender 6
volume: 0
brightness: 100
z_min: 0
z_max: 400
```

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
