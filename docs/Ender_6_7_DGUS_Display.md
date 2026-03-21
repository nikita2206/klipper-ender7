# Ender 6/7 DGUS Display Setup

This guide covers installing this Klipper fork with DGUS display support
on a Creality Ender 6 or Ender 7 printer.

## Prerequisites

Flash the DGUS Reloaded firmware onto your display:

- [Flashing instructions](https://github.com/Desuuuu/DGUS-reloaded-Klipper/wiki/Flashing-the-firmware)
- [Firmware releases](https://github.com/Desuuuu/DGUS-reloaded-Klipper/releases)

## Klipper installation

1. Prepare an SD card with Raspberry Pi OS Lite (64-bit) using Raspberry
   Pi Imager. Set a username/password and enable SSH.

2. Enable SPI and I2C:
   ```bash
   sudo raspi-config
   ```

3. Update the system and install dependencies:
   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install git -y
   sudo shutdown -r now
   ```

4. Install [KIAUH](https://github.com/dw-0/kiauh):
   ```bash
   git clone https://github.com/dw-0/kiauh.git
   ./kiauh/kiauh.sh
   ```
   Use KIAUH to install Klipper, then exit.

5. Replace Klipper with this fork:
   ```bash
   rm -rf ~/klipper
   git clone https://github.com/nikita2206/klipper-ender7.git ~/klipper
   ```

6. Build and flash the MCU firmware:
   ```bash
   cd ~/klipper
   make menuconfig
   ```
   Configure for your board (STM32 for Ender 6/7), then:
   ```bash
   make
   ```
   Rename `out/klipper.bin` (e.g. `klipper_new.bin`), copy to a FAT32
   formatted SD card (4096 byte allocation), insert into the printer,
   power on, wait ~1 minute, then power off.

7. Install Moonraker and Fluidd via KIAUH:
   ```bash
   ~/kiauh/kiauh.sh
   ```

8. (Optional) Build the host MCU for ADXL345 support:
   ```bash
   cd ~/klipper
   make clean
   make menuconfig  # select "Linux process"
   sudo service klipper stop
   make flash
   sudo service klipper start
   sudo usermod -a -G tty pi
   sudo shutdown -r now
   ```

## Klipper configuration

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

### Optional: ADXL345 accelerometer

```ini
[mcu rpi]
serial: /tmp/klipper_host_mcu

[adxl345]
cs_pin: rpi:None

[resonance_tester]
accel_chip: adxl345
probe_points:
    130, 130, 20

[input_shaper]
shaper_freq_x: 67.2
shaper_type_x: ei
shaper_freq_y: 72.8
shaper_type_y: mzv
```

### Optional: screws tilt adjust

```ini
[screws_tilt_adjust]
horizontal_move_z: 5
screw1: 63,243
screw1_name: back left
screw2: 253,243
screw2_name: back right
screw3: 64,53
screw3_name: front left
screw4: 254,53
screw4_name: front right
```

### Optional: BLTouch

If using a BLTouch, comment out the manual Z endstop lines and uncomment
the BLTouch lines in your printer config. Set your X/Y probe offsets per
[this guide](https://www.youtube.com/watch?v=FKvPU2nwdts).

You may also want to add:
```ini
stow_on_each_sample: false
probe_with_touch_mode: true
```

## Calibration

- **Input shaper (ADXL):** https://www.klipper3d.org/Measuring_Resonances.html
- **PID tuning:**
  ```
  PID_CALIBRATE HEATER=extruder TARGET=200
  SAVE_CONFIG
  PID_CALIBRATE HEATER=heater_bed TARGET=60
  SAVE_CONFIG
  ```
- **Extruder rotation distance:** https://www.service-uplink.de/esteps_cal/calculator.php
- **Z offset (BLTouch):** https://www.kevink.org/calibrate-z-offset-with-klipper/
