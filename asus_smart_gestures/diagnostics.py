"""System diagnostics and health check tool (asus-smart-gestures --doctor)."""

import grp
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .detector import scan_touchpads

_CHECK = "\033[32m[PASS]\033[0m"
_WARN = "\033[33m[WARN]\033[0m"
_FAIL = "\033[31m[FAIL]\033[0m"


def run_doctor() -> bool:
    """Run full environment health check and print structured diagnostic report."""
    print("=" * 65)
    print(" ASUS Smart Gestures - System Diagnostic Doctor")
    print("=" * 65)

    all_passed = True

    # 1. Python version check
    py_ver = sys.version_info
    if py_ver >= (3, 10):
        print(f"{_CHECK} Python Version: {py_ver.major}.{py_ver.minor}.{py_ver.micro}")
    else:
        print(f"{_FAIL} Python Version: {py_ver.major}.{py_ver.minor} (Must be >= 3.10)")
        all_passed = False

    # 2. Kernel uinput module check
    uinput_loaded = Path("/sys/module/uinput").exists() or (
        Path("/proc/modules").exists() and "uinput" in Path("/proc/modules").read_text()
    )
    if uinput_loaded:
        print(f"{_CHECK} Kernel Module: 'uinput' is loaded")
    else:
        print(f"{_WARN} Kernel Module: 'uinput' is not loaded (run: sudo modprobe uinput)")

    # 3. /dev/uinput device accessibility
    uinput_dev = Path("/dev/uinput")
    if uinput_dev.exists():
        if os.access(uinput_dev, os.W_OK):
            print(f"{_CHECK} Device Access: {uinput_dev} is writable")
        else:
            print(f"{_WARN} Device Access: {uinput_dev} exists but is not writable by current user")
            print("       -> Required when running daemon as current user (or run with sudo)")
    else:
        print(f"{_FAIL} Device Access: {uinput_dev} does not exist")
        all_passed = False

    # 4. User permissions / groups
    is_root = os.geteuid() == 0
    if is_root:
        print(f"{_CHECK} Privileges: Running as root (full hardware access)")
    else:
        groups: list[str] = []
        for gid in os.getgroups():
            try:
                groups.append(grp.getgrgid(gid).gr_name)
            except KeyError:
                groups.append(str(gid))

        has_input = "input" in groups
        has_uinput = "uinput" in groups
        if has_input and has_uinput:
            print(f"{_CHECK} Privileges: Member of 'input' and 'uinput' groups")
        else:
            print(f"{_WARN} Privileges: Running as non-root (groups: {', '.join(groups)}).")
            print("       -> Daemon normally runs as a root systemd service.")

    # 5. Touchpad scan
    touchpads = scan_touchpads()
    if touchpads:
        print(f"{_CHECK} Touchpads Detected: {len(touchpads)} found")
        for i, tp in enumerate(touchpads, 1):
            print(f"       [{i}] {tp.name} -> {tp.path} (X: {tp.width}px, Y: {tp.height}px)")
    else:
        print(f"{_FAIL} Touchpads Detected: No multitouch trackpad found in /dev/input")
        print("       -> Ensure you have read access to /dev/input/event* (run with sudo)")
        all_passed = False

    # 6. Systemd service status
    systemctl = shutil.which("systemctl")
    if systemctl:
        try:
            res = subprocess.run(
                ["systemctl", "is-active", "asus-smart-gestures"],
                capture_output=True,
                text=True,
                check=False,
            )
            state = res.stdout.strip()
            if state == "active":
                print(
                    f"{_CHECK} Systemd Service: 'asus-smart-gestures.service' is ACTIVE (running)"
                )
            elif state in ("inactive", "failed"):
                print(f"{_WARN} Systemd Service: 'asus-smart-gestures.service' is {state.upper()}")
            else:
                print(f"{_WARN} Systemd Service: State is '{state}'")
        except Exception as err:
            print(f"{_WARN} Systemd Service: Could not query service status ({err})")
    else:
        print(f"{_WARN} Systemd Service: systemctl binary not found")

    # 7. Configuration file
    conf_path = Path("/etc/asus-smart-gestures.conf")
    if conf_path.is_file():
        print(f"{_CHECK} Configuration: {conf_path} exists")
    else:
        print(f"{_WARN} Configuration: {conf_path} not found (using default internal settings)")

    print("=" * 65)
    if all_passed:
        print("RESULT: System is healthy and ready for ASUS Smart Gestures.")
    else:
        print("RESULT: Some required checks failed. Please address errors above.")
    print("=" * 65)

    return all_passed
