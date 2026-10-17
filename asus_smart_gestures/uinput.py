"""uinput virtual keyboard implementation for emitting media & brightness keys."""

import fcntl
import os
import struct
import time
from typing import Iterable, Set

EV_SYN = 0x00
EV_KEY = 0x01
SYN_REPORT = 0x00

UI_SET_EVBIT = 0x40045564
UI_SET_KEYBIT = 0x40045565
UI_DEV_CREATE = 0x5501
UI_DEV_DESTROY = 0x5502

# Standard Linux input keycodes (linux/input-event-codes.h)
KEY_VOLUMEDOWN = 114
KEY_VOLUMEUP = 115
KEY_PREVIOUSSONG = 165
KEY_NEXTSONG = 163
KEY_PLAYPAUSE = 164
KEY_BRIGHTNESSDOWN = 224
KEY_BRIGHTNESSUP = 225

FMT = "llHHi"

KEY_NAMES = {
    KEY_VOLUMEUP: "VOLUMEUP",
    KEY_VOLUMEDOWN: "VOLUMEDOWN",
    KEY_BRIGHTNESSUP: "BRIGHTNESSUP",
    KEY_BRIGHTNESSDOWN: "BRIGHTNESSDOWN",
    KEY_NEXTSONG: "NEXTSONG",
    KEY_PREVIOUSSONG: "PREVIOUSSONG",
    KEY_PLAYPAUSE: "PLAYPAUSE",
}


class UInputDevice:
    """Creates a virtual keyboard via Linux /dev/uinput."""

    def __init__(self, name: str = "asus-smart-gestures", keys: Iterable[int] = ()):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_SYN)

        key_set: Set[int] = set(keys) if keys else set(KEY_NAMES.keys())
        for k in key_set:
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, k)

        # struct uinput_user_dev (80 chars name, id, ff_effects_max, absmax/absmin)
        dev = struct.pack(
            "80sHHHHi" + "i" * 256,
            name.encode(),
            0x03, 0x1209,  # BUS_USB, vendor
            0x330C, 1, 0,  # product, version, ff_effects_max
            *([0] * 256),
        )
        os.write(self.fd, dev)
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        time.sleep(0.2)

    def tap(self, code: int) -> None:
        """Send key press, SYN, release, SYN."""
        for t, c, v in (
            (EV_KEY, code, 1), (EV_SYN, SYN_REPORT, 0),
            (EV_KEY, code, 0), (EV_SYN, SYN_REPORT, 0),
        ):
            os.write(self.fd, struct.pack(FMT, 0, 0, t, c, v))

    def close(self) -> None:
        """Destroy virtual uinput device."""
        try:
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        except OSError:
            pass
        os.close(self.fd)
