# Troubleshooting & Diagnostics Guide

This guide covers solutions to common setup, permission, and hardware detection issues.

---

## 1. Quick Diagnostics with `--doctor`

Always start by running the built-in diagnostic tool:

```bash
sudo asus-smart-gestures --doctor
```

It audits your kernel modules, device permissions, touchpad detection, configuration, and systemd service status:

```text
=================================================================
 ASUS Smart Gestures - System Diagnostic Doctor
=================================================================
[PASS] Python Version: 3.14.7
[PASS] Kernel Module: 'uinput' is loaded
[PASS] Device Access: /dev/uinput is writable
[PASS] Privileges: Running as root (full hardware access)
[PASS] Touchpads Detected: 1 found
       [1] ASCE1203:00 04F3:330C Touchpad -> /dev/input/event10 (X: 3987px, Y: 2579px)
[PASS] Systemd Service: 'asus-smart-gestures.service' is ACTIVE (running)
[PASS] Configuration: /etc/asus-smart-gestures.conf exists
=================================================================
RESULT: System is healthy and ready for ASUS Smart Gestures.
=================================================================
```

---

## 2. Common Issues & Solutions

### A. The edge strips don't change volume or brightness

1. **Check if the daemon is receiving touch events**:
   ```bash
   journalctl -u asus-smart-gestures -f
   ```
   Slide your finger along the left edge. If you see:
   ```text
   Touch start at (120, 1500) -> [LEFT EDGE]
     -> Emitting VOLUMEUP
   ```
   The daemon is functioning correctly! The issue is that your desktop environment has not mapped `XF86AudioRaiseVolume` or `XF86MonBrightnessUp`.

2. **Verify Desktop Key Bindings**:
   - **Hyprland / Omarchy**: Built-in defaults handle both. Verify using:
     ```bash
     which omarchy-audio-output-volume omarchy-brightness-display
     ```
   - **Sway / i3**: Add standard binds in `~/.config/sway/config`:
     ```i3
     bindsym XF86AudioRaiseVolume exec pactl set-sink-volume @DEFAULT_SINK@ +5%
     bindsym XF86AudioLowerVolume exec pactl set-sink-volume @DEFAULT_SINK@ -5%
     bindsym XF86MonBrightnessUp exec brightnessctl set +5%
     bindsym XF86MonBrightnessDown exec brightnessctl set 5%-
     ```
   - **GNOME / KDE Plasma**: Supported out of the box.

---

### B. Gestures trigger accidentally while typing or moving cursor

**Solution:** Reduce the edge strip percentage in `/etc/asus-smart-gestures.conf`:

```ini
[zones]
# Default is 7.0%. Reduce to 4.5% - 5.5% for narrower strips
edge_x_percent = 5.0
```

Then restart the service:
```bash
sudo systemctl restart asus-smart-gestures
```

---

### C. Volume or brightness changes too fast or too slow

**Solution:** Adjust `step_travel_percent` in `/etc/asus-smart-gestures.conf`:
- **Too fast (too sensitive):** Increase to `6.0` or `7.0`.
- **Too slow (too sluggish):** Decrease to `2.5` or `3.0`.

```ini
[zones]
step_travel_percent = 5.0
```

---

### D. Permission denied accessing `/dev/uinput` or `/dev/input/event*`

The daemon requires hardware access.
- For system service: Handled automatically by systemd (`root` execution).
- For running manually in terminal:
  ```bash
  sudo asus-smart-gestures --calibrate
  ```
  Or add your user to the `input` and `uinput` groups:
  ```bash
  sudo usermod -aG input,uinput $USER
  ```
  *(Log out and back in for group changes to take effect).*

---

### E. "uinput kernel module not loaded"

Load it dynamically:
```bash
sudo modprobe uinput
```

Ensure it persists across boots:
```bash
echo "uinput" | sudo tee /etc/modules-load.d/uinput.conf
```

---

## 3. Calibrating Your Specific Trackpad

To see exact pixel coordinates and percentage boundaries live:

```bash
sudo asus-smart-gestures --calibrate
```

Slide your fingers on the edges to verify that the zones align with the physical markings on your laptop trackpad.
