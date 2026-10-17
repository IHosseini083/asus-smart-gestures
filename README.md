# ASUS Smart Gestures for Linux

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-success.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Recreates the official ASUS Smart Gestures (found in MyASUS on Windows) for Linux on ASUS laptops (ExpertBook, ZenBook, VivoBook, ROG).

Enables natural single-finger edge-slide controls directly on your laptop trackpad:
- Left Edge (Slide Up / Down): Master Volume Up / Down
- Right Edge (Slide Up / Down): Display Backlight Brightness Up / Down
- Top Edge (Optional, Slide Left / Right): Previous / Next Media Track

---

## Architecture & How It Works

```text
+-------------------------------------------------------------+
|                 ASUS Precision Touchpad                     |
|  (ELAN / FocalTech / Synaptics via hid-multitouch kernel)   |
+------------------------------+------------------------------+
                               |
                /dev/input/eventX raw stream
                               |
                               v
            +------------------------------------+
            │        asus-smart-gestures         │
            │          (Userspace Daemon)        │
            +------------------+-----------------+
                               |
            +------------------+------------------+
     [Touch in Center]                     [Touch in Edge Strip]
            │                                     │
            v                                     v
   Normal cursor move                     Grab event stream (EVIOCGRAB)
(Untouched, zero latency)                 Translate vertical/horizontal slide
                                          Emit XF86 keycodes via /dev/uinput
                                                  │
                                                  v
                                      +-----------------------+
                                      │ Desktop Environment   │
                                      │ (Hyprland / Omarchy / │
                                      │  GNOME / KDE / Sway)  │
                                      +-----------------------+
                                                  │
                                                  v
                                         Native On-Screen HUD
                                        (Volume / Brightness)
```

---

## Features

- Pixel-Perfect Auto-Calibration: Queries hardware resolution dynamically via kernel `EVIOCGABS` ioctls.
- Fail-Safe Grab Protection: Traps signals (`SIGINT`, `SIGTERM`, `SIGHUP`) and registers `atexit` handlers so the touchpad never locks up, even if killed.
- Hardened Systemd Sandbox: Ships with strict systemd security sandboxing (`ProtectSystem=strict`, `ProtectHome=true`, `NoNewPrivileges=true`).
- Built-in System Doctor (`--doctor`): Audits permissions, uinput module, service state, and touchpad detection.
- Interactive Visualizer (`--calibrate`): Displays real-time coordinate percentages and active edge boundaries.
- Zero External Dependencies: Built with pure modern Python 3 (Python 3.10+ standard library only).

---

## Supported & Tested Hardware

Works on any ASUS laptop featuring an internal multitouch trackpad:

| Laptop Model | Touchpad Hardware ID | Status |
| :--- | :--- | :--- |
| ASUS ExpertBook P5 | `ASCE1203:00 04F3:330C` | Supported (Confirmed) |
| ASUS ZenBook S16 | `ASUF1209:00 2808:0219` | Supported |
| ASUS ZenBook 14 OLED | `ELAN / FocalTech` | Supported |
| ASUS VivoBook Series | Multitouch Precision | Supported |
| ASUS ROG Zephyrus | Multitouch Precision | Supported |

---

## Installation

### Prerequisites
- Python >= 3.10 (Standard library)
- Linux Kernel with `uinput` enabled
- Systemd-based Linux distribution (Arch, Omarchy, Ubuntu, Fedora, Debian, openSUSE)

### 1. One-Step Installer (Recommended)

```bash
git clone https://github.com/IHosseini083/asus-smart-gestures.git
cd asus-smart-gestures
sudo ./install.sh
```

The installer:
- Checks dependencies (Python >= 3.10, systemd, uinput)
- Deploys library to `/usr/local/lib/asus-smart-gestures`
- Installs binary launcher to `/usr/local/bin/asus-smart-gestures`
- Generates `/etc/asus-smart-gestures.conf`
- Enables and loads `uinput` module at boot
- Enables and starts `asus-smart-gestures.service`

### 2. Arch Linux / Omarchy (PKGBUILD)

```bash
cd asus-smart-gestures/pkg
makepkg -si
sudo systemctl enable --now asus-smart-gestures
```

---

## Diagnostics & Health Check

Run the system doctor anytime to verify your configuration and environment:

```bash
sudo asus-smart-gestures --doctor
```

---

## Interactive Calibration

Run the calibration tool to visualize your trackpad boundaries live in the terminal:

```bash
sudo asus-smart-gestures --calibrate
```

Slide your fingers along the edges to verify that the active zones match your laptop's physical markings.

---

## Configuration

Settings are stored in `/etc/asus-smart-gestures.conf` (or `~/.config/asus-smart-gestures/config.conf`):

```ini
[general]
# Specific device path (leave blank for automatic detection)
# device = /dev/input/event10
dry_run = false
log_level = INFO

[zones]
# Width of left/right slider strips as % of touchpad width (default: 7.0%)
edge_x_percent = 7.0

# Bottom area percentage to ignore (clickpad click isolation, default: 15.0%)
bottom_ignore_percent = 15.0

# Vertical travel required for each volume/brightness step (default: 4.0%)
step_travel_percent = 4.0

# Optional top edge media scrubbing (previous / next track)
enable_top_edge = false
top_edge_percent = 8.0
top_step_travel_percent = 5.0

[actions]
# Supported actions: volume, brightness, media, none
left_edge = volume
right_edge = brightness
top_edge = media

# Invert slide directions (default: sliding UP increases value)
invert_left = false
invert_right = false
invert_top = false
```

Restart the daemon after updating configuration:
```bash
sudo systemctl restart asus-smart-gestures
```

---

## CLI Reference

```text
asus-smart-gestures [OPTIONS]

Options:
  -h, --help            Show help message
  --version             Show program version
  --doctor              Audit system environment and report hardware/privilege health
  --scan                Scan and list all detected multitouch trackpads
  --calibrate           Launch interactive terminal visualizer
  --dry                 Dry run: trace touches without capturing device or emitting keys
  -c, --config PATH     Path to custom configuration file
  -d, --device PATH     Path to specific input device
  -v, --verbose         Enable verbose debug logging
  -q, --quiet           Suppress informational messages
  --duration SECONDS    Run for N seconds then exit (testing)
```

---

## Uninstallation

To cleanly remove all components:

```bash
sudo ./uninstall.sh
```

To also delete configuration files:
```bash
sudo ./uninstall.sh --purge
```

---

## Documentation

- [Troubleshooting Guide](TROUBLESHOOTING.md) - Resolving keybindings, permissions, and calibration issues.
- [Security Policy](SECURITY.md) - Privilege architecture and fail-safe grab release mechanisms.
- [Contributing](CONTRIBUTING.md) - Development workflow, Ruff/Mypy validation, and hardware submission.

---

## License

[MIT License](LICENSE) (c) 2026 Iliya
