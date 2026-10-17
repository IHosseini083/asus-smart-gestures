"""Universal touchpad detection and geometry query for ASUS laptops."""

import fcntl
import glob
import os
import struct
from typing import Dict, List, Optional, Tuple

EVIOCGNAME_LEN = 256
EVIOCGPROP_LEN = 8


def _ioc(dir_: int, type_: str, nr: int, size: int) -> int:
    return (dir_ << 30) | (size << 16) | (ord(type_) << 8) | nr


def EVIOCGNAME(length: int) -> int:
    return _ioc(2, "E", 0x06, length)


def EVIOCGABS(axis: int) -> int:
    return _ioc(2, "E", 0x40 + axis, 24)


def EVIOCGBIT(ev_type: int, length: int) -> int:
    return _ioc(2, "E", 0x20 + ev_type, length)


def EVIOCGPROP(length: int) -> int:
    return _ioc(2, "E", 0x09, length)


EV_KEY = 0x01
EV_ABS = 0x03

ABS_MT_POSITION_X = 0x35  # 53
ABS_MT_POSITION_Y = 0x36  # 54
BTN_TOUCH = 0x14A         # 330
INPUT_PROP_POINTER = 0x00
INPUT_PROP_BUTTONPAD = 0x02


def get_device_name(fd: int) -> str:
    try:
        buf = bytearray(EVIOCGNAME_LEN)
        fcntl.ioctl(fd, EVIOCGNAME(EVIOCGNAME_LEN), buf)
        return buf.split(b"\x00", 1)[0].decode(errors="replace")
    except OSError:
        return ""


def get_abs_info(fd: int, axis: int) -> Optional[Tuple[int, int]]:
    """Return (min, max) for an absolute axis."""
    try:
        buf = bytearray(24)
        fcntl.ioctl(fd, EVIOCGABS(axis), buf)
        _val, minimum, maximum, _fuzz, _flat, _res = struct.unpack("6i", buf)
        if maximum > minimum:
            return minimum, maximum
    except OSError:
        pass
    return None


def has_bit(buf: bytearray, bit: int) -> bool:
    byte_idx = bit // 8
    bit_idx = bit % 8
    if byte_idx < len(buf):
        return bool(buf[byte_idx] & (1 << bit_idx))
    return False


def is_touchpad(fd: int, name: str) -> bool:
    """Determine if device is a multitouch touchpad."""
    # Check ABS bits
    abs_bits = bytearray(64)
    try:
        fcntl.ioctl(fd, EVIOCGBIT(EV_ABS, len(abs_bits)), abs_bits)
    except OSError:
        return False

    has_mt_x = has_bit(abs_bits, ABS_MT_POSITION_X)
    has_mt_y = has_bit(abs_bits, ABS_MT_POSITION_Y)
    if not (has_mt_x and has_mt_y):
        return False

    # Check KEY bits for BTN_TOUCH
    key_bits = bytearray(96)
    try:
        fcntl.ioctl(fd, EVIOCGBIT(EV_KEY, len(key_bits)), key_bits)
    except OSError:
        return False

    if not has_bit(key_bits, BTN_TOUCH):
        return False

    name_lower = name.lower()
    # Explicit exclusion of touchscreen / tablets
    if "touchscreen" in name_lower or "pen" in name_lower or "tablet" in name_lower:
        return False

    if "touchpad" in name_lower or "trackpad" in name_lower:
        return True

    # Check input properties for pointer/buttonpad
    prop_bits = bytearray(EVIOCGPROP_LEN)
    try:
        fcntl.ioctl(fd, EVIOCGPROP(EVIOCGPROP_LEN), prop_bits)
        if has_bit(prop_bits, INPUT_PROP_POINTER) or has_bit(prop_bits, INPUT_PROP_BUTTONPAD):
            return True
    except OSError:
        pass

    return False


def scan_touchpads() -> List[Dict[str, any]]:
    """Scan all /dev/input/event* and return candidate touchpads."""
    devices = []
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
        except OSError:
            continue

        try:
            name = get_device_name(fd)
            if is_touchpad(fd, name):
                x_range = get_abs_info(fd, ABS_MT_POSITION_X)
                y_range = get_abs_info(fd, ABS_MT_POSITION_Y)
                devices.append({
                    "path": path,
                    "name": name,
                    "x_range": x_range or (0, 3987),
                    "y_range": y_range or (0, 2579),
                })
        finally:
            os.close(fd)

    return devices


def find_best_touchpad(preferred_path: Optional[str] = None) -> Tuple[str, str, Tuple[int, int], Tuple[int, int]]:
    """Select the best touchpad or raise RuntimeError."""
    if preferred_path:
        if not os.path.exists(preferred_path):
            raise RuntimeError(f"Configured device path not found: {preferred_path}")
        fd = os.open(preferred_path, os.O_RDONLY | os.O_NONBLOCK)
        try:
            name = get_device_name(fd)
            x_range = get_abs_info(fd, ABS_MT_POSITION_X) or (0, 3987)
            y_range = get_abs_info(fd, ABS_MT_POSITION_Y) or (0, 2579)
            return preferred_path, name, x_range, y_range
        finally:
            os.close(fd)

    candidates = scan_touchpads()
    if not candidates:
        raise RuntimeError("No multitouch touchpad found in /dev/input/event*")

    # Priority 1: ASUS-specific touchpad IDs or names
    for dev in candidates:
        name = dev["name"].lower()
        if any(token in name for token in ["asuf", "asce", "asue", "asus", "04f3:"]):
            return dev["path"], dev["name"], dev["x_range"], dev["y_range"]

    # Priority 2: Standard touchpad
    first = candidates[0]
    return first["path"], first["name"], first["x_range"], first["y_range"]
