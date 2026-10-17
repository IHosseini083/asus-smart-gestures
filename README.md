# ASUS Smart Gestures for Linux 🚀

Recreates the official **ASUS Smart Gestures** (found in MyASUS on Windows) for Linux on ASUS laptops (**ExpertBook, ZenBook, VivoBook, ROG**).

Enables natural single-finger edge-slide controls directly on your laptop's trackpad:
- **Left Edge (Slide Up / Down):** Master Volume Up / Down
- **Right Edge (Slide Up / Down):** Display Backlight Brightness Up / Down
- **Top Edge (Optional, Slide Left / Right):** Previous / Next Media Track

---

## Why is this needed?

On Windows, ASUS includes proprietary drivers that interpret touches along the edges of the touchpad. On Linux, the touchpad binds to the generic `hid-multitouch` driver, which reports only raw multitouch coordinates — leaving edge gestures completely unhandled.

`asus-smart-gestures` monitors the raw evdev stream from the touchpad in userspace:
1. **Zero latency cursor movement:** Touches that start inside the central touchpad area are untouched and pass through normally.
2. **Edge detection:** When a touch begins in an edge strip (e.g. left ~7% or right ~7%), it grabs the device only for that touch, translating vertical travel into standard `XF86Audio` / `XF86MonBrightness` key events via a virtual `/dev/uinput` device.
3. **Desktop integration:** Emits standard hardware multimedia keys, seamlessly triggering your desktop's native OSD notifications (Hyprland, Omarchy, GNOME, KDE, Sway, i3).

---

## Supported & Tested Hardware

Works with any ASUS Precision Touchpad (ELAN, Synaptics, FocalTech, ASUE, ASCE, ASUF controllers):

| Laptop Model | Touchpad Hardware ID | Status |
| :--- | :--- | :--- |
| **ASUS ExpertBook P5** | `ASCE1203:00 04F3:330C` | ✅ Confirmed working |
| **ASUS ZenBook S16** | `ASUF1209:00 2808:0219` | ✅ Supported |
| **ASUS ZenBook 14 OLED** | `ELAN / FocalTech` | ✅ Supported |
| **Other ASUS Laptops** | Generic Multitouch Precision | ✅ Supported (Auto-calibrated) |

---

## Installation

### Prerequisites
- Python 3.8+ (Standard library only; zero external pip dependencies)
- Systemd
- Linux Kernel with `uinput` support enabled (standard on Arch, Ubuntu, Fedora, Debian)

### Option 1: Quick Install (Any distro with systemd)

```bash
git clone https://github.com/your-username/asus-smart-gestures.git
cd asus-smart-gestures
sudo ./install.sh
```

The installer:
- Deploys the service to `/usr/local/bin/asus-smart-gestures`
- Configures `/etc/asus-smart-gestures.conf`
- Enables and loads the `uinput` module
- Enables and starts the `asus-smart-gestures.service` systemd unit

### Option 2: Arch Linux / Omarchy (PKGBUILD)

```bash
cd asus-smart-gestures/pkg
makepkg -si
sudo systemctl enable --now asus-smart-gestures
```

---

## Testing & Calibration

Check detected touchpads:
```bash
sudo asus-smart-gestures --scan
```

Test gestures without altering volume or grabbing the cursor:
```bash
sudo asus-smart-gestures --dry
```

Run interactive visual calibration:
```bash
sudo asus-smart-gestures --calibrate
```
Slide your fingers across the edges of the trackpad to view real-time boundary percentages.

---

## Configuration

Settings are configured in `/etc/asus-smart-gestures.conf` (or `~/.config/asus-smart-gestures/config.conf`):

```ini
[zones]
# Width of left/right slider strips as % of touchpad width
edge_x_percent = 7.0

# Bottom area percentage to ignore (clickpad click isolation)
bottom_ignore_percent = 15.0

# Travel distance required to emit one step (volume/brightness step)
step_travel_percent = 4.0

# Enable optional top edge media scrubbing
enable_top_edge = false

[actions]
left_edge = volume
right_edge = brightness
top_edge = media

# Invert slide directions
invert_left = false
invert_right = false
invert_top = false
```

After modifying the configuration, restart the daemon:
```bash
sudo systemctl restart asus-smart-gestures
```

---

## Logs & Monitoring

To monitor gesture events in real-time:
```bash
journalctl -u asus-smart-gestures -f
```

---

## Uninstallation

```bash
sudo ./uninstall.sh
```

---

## License

MIT © 2026 Iliya
