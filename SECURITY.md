# Security & Threat Model

This document outlines the security architecture, privilege model, and fail-safe mechanisms implemented in `asus-smart-gestures`.

---

## Privileges & Device Access

`asus-smart-gestures` interacts directly with Linux kernel input subsystems:
1. **Raw Event Stream (`/dev/input/event*`)**: Requires read access to capture finger coordinates and `EVIOCGRAB` ioctl permission.
2. **Virtual Keyboard (`/dev/uinput`)**: Requires write access to create a virtual input device and emit synthetic `XF86Audio` / `XF86MonBrightness` key events.

By default, the daemon runs as a hardened systemd service under `root` with strong sandboxing restrictions.

---

## Fail-Safe Mechanism (Lockup Prevention)

### The Problem
When `EVIOCGRAB` is active on an input device, the Linux kernel gives the holding process exclusive control of all events from that device. If a daemon crashes, hangs, or is abruptly killed (`SIGTERM`, `SIGINT`) while holding a grab, the physical touchpad would normally lock up and stop responding until a system reboot.

### The Solution in `asus-smart-gestures`
1. **Scoped Grabs**: The device is **only grabbed** when a touch begins inside an edge strip (left, right, or top). Touches in the middle of the pad are never grabbed.
2. **Signal Trapping**: Intercepts `SIGINT`, `SIGTERM`, and `SIGHUP` to immediately release the grab (`fcntl.ioctl(fd, EVIOCGRAB, 0)`) before exiting.
3. **`atexit` Registry**: Registers an ungrab and file descriptor cleanup callback with Python's standard `atexit` engine, ensuring ungrab executes even during unhandled Python exceptions.
4. **Context Management**: Virtual `/dev/uinput` devices are guarded by standard context managers (`__enter__` and `__exit__`), destroying virtual nodes cleanly upon exit.

---

## Systemd Security Sandboxing

The provided systemd unit (`asus-smart-gestures.service`) applies kernel namespace and sandbox restrictions:

```ini
ProtectSystem=strict            # Mounts /usr, /boot, /etc as read-only
ProtectHome=true                # /home and /root are completely inaccessible
ProtectKernelTunables=true      # Kernel sysctls cannot be altered
ProtectControlGroups=true       # cgroup hierarchies cannot be modified
NoNewPrivileges=true            # Child processes cannot escalate privileges
MemoryDenyWriteExecute=true     # Mitigates W^X memory exploits
RestrictRealtime=true           # Prevents real-time scheduling abuse
DeviceAllow=char-input rw       # Restricts device access strictly to inputs (char-input device group)
DeviceAllow=/dev/uinput rw      # Restricts device access strictly to uinput
```

---

## Reporting Vulnerabilities

If you discover a security vulnerability in `asus-smart-gestures`, please do not open a public issue. Instead, report it privately via [GitHub Security Advisories](https://github.com/IHosseini083/asus-smart-gestures/security/advisories/new) or contact the maintainer directly.
