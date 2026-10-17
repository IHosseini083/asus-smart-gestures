"""Context-managed virtual keyboard device via Linux uinput."""

import fcntl
import os
import struct
import time
from collections.abc import Iterable
from contextlib import AbstractContextManager, suppress
from pathlib import Path
from types import TracebackType

from .constants import (
    EV_KEY,
    EV_SYN,
    INPUT_EVENT_FMT,
    SYN_REPORT,
    UI_DEV_CREATE,
    UI_DEV_DESTROY,
    UI_SET_EVBIT,
    UI_SET_KEYBIT,
    KeyCode,
)
from .logging import get_logger

UINPUT_PATH = Path("/dev/uinput")


class UInputDevice(AbstractContextManager["UInputDevice"]):
    """Virtual keyboard device for emitting hardware multimedia and brightness keycodes."""

    def __init__(
        self,
        name: str = "asus-smart-gestures",
        keys: Iterable[KeyCode] | None = None,
    ) -> None:
        self._name = name
        self._keys = set(keys) if keys is not None else set(KeyCode)
        self._fd: int | None = None
        self._open()

    def _open(self) -> None:
        logger = get_logger()
        if not UINPUT_PATH.exists():
            raise FileNotFoundError(
                "/dev/uinput does not exist. Ensure the uinput kernel module is loaded ('modprobe uinput')."
            )

        try:
            self._fd = os.open(UINPUT_PATH, os.O_WRONLY | os.O_NONBLOCK)
        except PermissionError as err:
            raise PermissionError(
                "Permission denied opening /dev/uinput. Root privileges or uinput group access required."
            ) from err

        try:
            fcntl.ioctl(self._fd, UI_SET_EVBIT, EV_KEY)
            fcntl.ioctl(self._fd, UI_SET_EVBIT, EV_SYN)
            for k in self._keys:
                fcntl.ioctl(self._fd, UI_SET_KEYBIT, int(k))

            dev = struct.pack(
                "80sHHHHi" + "i" * 256,
                self._name.encode("utf-8"),
                0x03,  # BUS_USB
                0x1209,  # Vendor ID
                0x330C,  # Product ID
                1,  # Version
                0,  # ff_effects_max
                *([0] * 256),
            )
            os.write(self._fd, dev)
            fcntl.ioctl(self._fd, UI_DEV_CREATE)
            time.sleep(0.15)
            logger.debug("Virtual uinput keyboard created: %s", self._name)
        except Exception:
            self.close()
            raise

    def tap(self, code: KeyCode) -> None:
        """Emit a key press followed immediately by release and synchronization."""
        if self._fd is None:
            raise RuntimeError("Cannot tap key: uinput device is closed")

        key_int = int(code)
        events = (
            (EV_KEY, key_int, 1),
            (EV_SYN, SYN_REPORT, 0),
            (EV_KEY, key_int, 0),
            (EV_SYN, SYN_REPORT, 0),
        )
        for ev_type, ev_code, ev_val in events:
            payload = struct.pack(INPUT_EVENT_FMT, 0, 0, ev_type, ev_code, ev_val)
            os.write(self._fd, payload)

    def close(self) -> None:
        """Destroy virtual device and close descriptor."""
        if self._fd is not None:
            with suppress(OSError):
                fcntl.ioctl(self._fd, UI_DEV_DESTROY)
            with suppress(OSError):
                os.close(self._fd)
            self._fd = None

    def __enter__(self) -> "UInputDevice":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()
