"""Hardware discovery and validation for ASUS and compatible touchpads."""

import fcntl
import stat
import struct
from dataclasses import dataclass
from pathlib import Path

from .constants import (
    ABS_MT_POSITION_X,
    ABS_MT_POSITION_Y,
    BTN_TOUCH,
    EV_ABS,
    EV_KEY,
    EVIOCGABS,
    EVIOCGBIT,
    EVIOCGNAME,
    EVIOCGPROP,
    INPUT_PROP_BUTTONPAD,
    INPUT_PROP_POINTER,
)
from .logging import get_logger

DEV_INPUT_DIR = Path("/dev/input")
MAX_NAME_LEN = 256
PROP_LEN = 8


@dataclass(slots=True, frozen=True)
class TouchpadInfo:
    """Discovered touchpad hardware information."""

    path: Path
    name: str
    x_min: int
    x_max: int
    y_min: int
    y_max: int

    @property
    def width(self) -> int:
        return self.x_max - self.x_min

    @property
    def height(self) -> int:
        return self.y_max - self.y_min


def _has_bit(buf: bytes | bytearray, bit: int) -> bool:
    byte_idx = bit // 8
    bit_idx = bit % 8
    if byte_idx < len(buf):
        return bool(buf[byte_idx] & (1 << bit_idx))
    return False


def get_device_name(fd: int) -> str:
    """Query evdev device name via EVIOCGNAME ioctl."""
    buf = bytearray(MAX_NAME_LEN)
    try:
        fcntl.ioctl(fd, EVIOCGNAME(MAX_NAME_LEN), buf)
        return buf.split(b"\x00", 1)[0].decode(errors="replace").strip()
    except OSError:
        return ""


def get_abs_range(fd: int, axis: int) -> tuple[int, int] | None:
    """Retrieve min and max coordinates for an absolute axis."""
    buf = bytearray(24)
    try:
        fcntl.ioctl(fd, EVIOCGABS(axis), buf)
        _val, minimum, maximum, _fuzz, _flat, _res = struct.unpack("6i", buf)
        if maximum > minimum:
            return minimum, maximum
    except OSError:
        pass
    return None


def is_valid_touchpad(fd: int, name: str) -> bool:
    """Verify that file descriptor represents a multi-touch trackpad."""
    # Check absolute axis capabilities
    abs_bits = bytearray(64)
    try:
        fcntl.ioctl(fd, EVIOCGBIT(EV_ABS, len(abs_bits)), abs_bits)
    except OSError:
        return False

    if not (_has_bit(abs_bits, ABS_MT_POSITION_X) and _has_bit(abs_bits, ABS_MT_POSITION_Y)):
        return False

    # Check key capabilities (must have BTN_TOUCH)
    key_bits = bytearray(96)
    try:
        fcntl.ioctl(fd, EVIOCGBIT(EV_KEY, len(key_bits)), key_bits)
    except OSError:
        return False

    if not _has_bit(key_bits, BTN_TOUCH):
        return False

    # Filter out touchscreens, tablets, and pens
    name_lower = name.lower()
    for blacklist in ("touchscreen", "pen", "stylus", "tablet", "digitizer"):
        if blacklist in name_lower:
            return False

    if "touchpad" in name_lower or "trackpad" in name_lower:
        return True

    # Check input properties for pointer/buttonpad
    prop_bits = bytearray(PROP_LEN)
    try:
        fcntl.ioctl(fd, EVIOCGPROP(PROP_LEN), prop_bits)
        if _has_bit(prop_bits, INPUT_PROP_POINTER) or _has_bit(prop_bits, INPUT_PROP_BUTTONPAD):
            return True
    except OSError:
        pass

    return False


def validate_device_path(path: Path | str) -> Path:
    """Sanitize and validate an input device path.

    Raises:
        ValueError: If path is not a valid character device or outside /dev/input.
    """
    resolved = Path(path).resolve()
    if not resolved.exists():
        raise ValueError(f"Device does not exist: {resolved}")

    # Must be a character device
    try:
        st = resolved.stat()
        if not stat.S_ISCHR(st.st_mode):
            raise ValueError(f"Path is not a character device: {resolved}")
    except OSError as err:
        raise ValueError(f"Cannot stat device path {resolved}: {err}") from err

    # Ensure device is within /dev/input
    if not (resolved.parent == DEV_INPUT_DIR or str(resolved).startswith("/dev/input/")):
        raise ValueError(f"Device path must be in /dev/input/: {resolved}")

    return resolved


def scan_touchpads() -> list[TouchpadInfo]:
    """Scan /dev/input for all multitouch touchpads."""
    logger = get_logger()
    touchpads: list[TouchpadInfo] = []

    if not DEV_INPUT_DIR.is_dir():
        logger.error("/dev/input directory does not exist")
        return touchpads

    for path in sorted(DEV_INPUT_DIR.glob("event*")):
        try:
            with path.open("rb") as f:
                fd = f.fileno()
                name = get_device_name(fd)
                if is_valid_touchpad(fd, name):
                    x_range = get_abs_range(fd, ABS_MT_POSITION_X) or (0, 3987)
                    y_range = get_abs_range(fd, ABS_MT_POSITION_Y) or (0, 2579)
                    touchpads.append(
                        TouchpadInfo(
                            path=path,
                            name=name,
                            x_min=x_range[0],
                            x_max=x_range[1],
                            y_min=y_range[0],
                            y_max=y_range[1],
                        )
                    )
        except PermissionError:
            logger.debug("Permission denied opening %s (requires root/input group)", path)
        except OSError as err:
            logger.debug("Error checking %s: %s", path, err)

    return touchpads


def find_touchpad(preferred_path: Path | str | None = None) -> TouchpadInfo:
    """Find the best matching touchpad device.

    Args:
        preferred_path: Optional path specified in configuration or CLI.

    Returns:
        TouchpadInfo for the target device.

    Raises:
        RuntimeError: If device cannot be found or accessed.
    """
    logger = get_logger()

    if preferred_path:
        valid_path = validate_device_path(preferred_path)
        try:
            with valid_path.open("rb") as f:
                fd = f.fileno()
                name = get_device_name(fd)
                x_range = get_abs_range(fd, ABS_MT_POSITION_X) or (0, 3987)
                y_range = get_abs_range(fd, ABS_MT_POSITION_Y) or (0, 2579)
                return TouchpadInfo(
                    path=valid_path,
                    name=name,
                    x_min=x_range[0],
                    x_max=x_range[1],
                    y_min=y_range[0],
                    y_max=y_range[1],
                )
        except PermissionError as err:
            raise RuntimeError(
                f"Permission denied accessing device {valid_path}. Run with sudo or join the 'input' group."
            ) from err
        except OSError as err:
            raise RuntimeError(f"Failed to access device {valid_path}: {err}") from err

    touchpads = scan_touchpads()
    if not touchpads:
        raise RuntimeError(
            "No multitouch touchpad found. Ensure you are running as root or user in the 'input' group."
        )

    # Priority 1: ASUS-specific touchpad identifiers
    asus_identifiers = ("asce", "asuf", "asue", "asus", "04f3:330c")
    for tp in touchpads:
        name_lower = tp.name.lower()
        if any(ident in name_lower for ident in asus_identifiers):
            logger.debug("Selected ASUS touchpad by identifier match: %s", tp.name)
            return tp

    # Priority 2: Return first candidate
    selected = touchpads[0]
    logger.debug("Selected first candidate touchpad: %s", selected.name)
    return selected
