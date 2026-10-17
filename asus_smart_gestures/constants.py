"""Constants, enumerations, and Linux evdev/uinput ioctl definitions."""

from enum import Enum, IntEnum

# Enumerations


class Zone(str, Enum):
    """Touchpad edge zones."""

    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    NONE = "none"

    def __str__(self) -> str:
        return self.value


class Action(str, Enum):
    """Supported gesture actions."""

    VOLUME = "volume"
    BRIGHTNESS = "brightness"
    MEDIA = "media"
    NONE = "none"

    def __str__(self) -> str:
        return self.value


class KeyCode(IntEnum):
    """Linux input keycodes from linux/input-event-codes.h."""

    VOLUMEDOWN = 114
    VOLUMEUP = 115
    PLAYPAUSE = 164
    NEXTSONG = 163
    PREVIOUSSONG = 165
    BRIGHTNESSDOWN = 224
    BRIGHTNESSUP = 225


# Linux Event Types and Codes

EV_SYN = 0x00
EV_KEY = 0x01
EV_REL = 0x02
EV_ABS = 0x03

SYN_REPORT = 0x00

BTN_TOUCH = 0x14A  # 330
BTN_TOOL_FINGER = 0x145

ABS_X = 0x00
ABS_Y = 0x01
ABS_MT_SLOT = 0x2F  # 47
ABS_MT_POSITION_X = 0x35  # 53
ABS_MT_POSITION_Y = 0x36  # 54
ABS_MT_TRACKING_ID = 0x39  # 57

INPUT_PROP_POINTER = 0x00
INPUT_PROP_DIRECT = 0x01
INPUT_PROP_BUTTONPAD = 0x02
INPUT_PROP_SEMI_MT = 0x03
INPUT_PROP_TOPBUTTONPAD = 0x04
INPUT_PROP_POINTING_STICK = 0x05
INPUT_PROP_ACCELEROMETER = 0x06

# Struct Format
INPUT_EVENT_FMT = "llHHi"


# ioctl Macros (Linux input subsystem)
def _ioc(dir_: int, type_: str, nr: int, size: int) -> int:
    return (dir_ << 30) | (size << 16) | (ord(type_) << 8) | nr


def EVIOCGNAME(length: int) -> int:
    """Get device name ioctl."""
    return _ioc(2, "E", 0x06, length)


def EVIOCGABS(axis: int) -> int:
    """Get abs info ioctl."""
    return _ioc(2, "E", 0x40 + axis, 24)


def EVIOCGBIT(ev_type: int, length: int) -> int:
    """Get event bits ioctl."""
    return _ioc(2, "E", 0x20 + ev_type, length)


def EVIOCGPROP(length: int) -> int:
    """Get device properties ioctl."""
    return _ioc(2, "E", 0x09, length)


EVIOCGRAB = 0x40044590

# uinput ioctl commands
UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502
