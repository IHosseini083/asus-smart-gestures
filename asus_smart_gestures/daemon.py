"""Core gesture daemon tracking touches, edge zones, and mapping slides to keys."""

import atexit
import contextlib
import fcntl
import os
import signal
import struct
import time
from collections.abc import Callable
from dataclasses import dataclass
from types import FrameType

from .config import GestureConfig
from .constants import (
    ABS_MT_POSITION_X,
    ABS_MT_POSITION_Y,
    ABS_MT_SLOT,
    ABS_MT_TRACKING_ID,
    EV_ABS,
    EV_SYN,
    EVIOCGRAB,
    INPUT_EVENT_FMT,
    SYN_REPORT,
    Action,
    KeyCode,
    Zone,
)
from .detector import TouchpadInfo
from .logging import get_logger
from .uinput import UInputDevice

EVENT_SIZE = struct.calcsize(INPUT_EVENT_FMT)


@dataclass(slots=True)
class TouchSlot:
    """State for a single multitouch tracking slot."""

    tracking_id: int | None = None
    x: int = 0
    y: int = 0


@dataclass(slots=True)
class ActiveGesture:
    """State for an active edge gesture being tracked."""

    zone: Zone
    slot_id: int
    step_ref_y: int
    step_ref_x: int
    start_x: int
    start_y: int


class GestureDaemon:
    """Monitors raw touchpad input and translates edge slides into system keys."""

    def __init__(self, touchpad: TouchpadInfo, config: GestureConfig) -> None:
        self.touchpad = touchpad
        self.cfg = config
        self.logger = get_logger()

        # Calculate coordinate thresholds from percentages
        width = touchpad.width
        height = touchpad.height

        self.edge_x = max(1, int((self.cfg.edge_x_percent / 100.0) * width))
        self.bottom_limit = touchpad.y_max - int((self.cfg.bottom_ignore_percent / 100.0) * height)
        self.step_y = max(1, int((self.cfg.step_travel_percent / 100.0) * height))

        self.top_limit = touchpad.y_min + int((self.cfg.top_edge_percent / 100.0) * height)
        self.step_x = max(1, int((self.cfg.top_step_travel_percent / 100.0) * width))

        self._uinput: UInputDevice | None = None
        self._fd: int | None = None
        self._is_grabbed = False
        self._running = False

    def _determine_zone(self, x: int, y: int) -> Zone:
        """Classify start coordinate into an edge zone or Zone.NONE."""
        # Bottom exclusion zone (clickpad physical click area)
        if y > self.bottom_limit:
            return Zone.NONE

        # Top horizontal slider
        if (
            self.cfg.enable_top_edge
            and y < self.top_limit
            and (self.touchpad.x_min + self.edge_x) <= x <= (self.touchpad.x_max - self.edge_x)
        ):
            return Zone.TOP

        # Left / right vertical sliders
        if x < (self.touchpad.x_min + self.edge_x):
            return Zone.LEFT
        if x > (self.touchpad.x_max - self.edge_x):
            return Zone.RIGHT

        return Zone.NONE

    def _resolve_keys(self, action: Action, invert: bool) -> tuple[KeyCode | None, KeyCode | None]:
        """Map action to (up_or_next_key, down_or_prev_key)."""
        pos: KeyCode | None = None
        neg: KeyCode | None = None

        if action == Action.VOLUME:
            pos, neg = KeyCode.VOLUMEUP, KeyCode.VOLUMEDOWN
        elif action == Action.BRIGHTNESS:
            pos, neg = KeyCode.BRIGHTNESSUP, KeyCode.BRIGHTNESSDOWN
        elif action == Action.MEDIA:
            pos, neg = KeyCode.NEXTSONG, KeyCode.PREVIOUSSONG

        if invert and pos is not None and neg is not None:
            return neg, pos
        return pos, neg

    def _set_device_grab(self, grab: bool) -> None:
        """Safely grab or ungrab device, ensuring fail-safe state."""
        if self._fd is None:
            return
        if grab and not self._is_grabbed and not self.cfg.dry_run:
            try:
                fcntl.ioctl(self._fd, EVIOCGRAB, 1)
                self._is_grabbed = True
                self.logger.debug("Device grabbed (exclusive access active)")
            except OSError as err:
                self.logger.warning("Failed to grab device: %s", err)
        elif not grab and self._is_grabbed:
            with contextlib.suppress(OSError):
                fcntl.ioctl(self._fd, EVIOCGRAB, 0)
            self.logger.debug("Device released (grab released)")
            self._is_grabbed = False

    def _cleanup(self) -> None:
        """Guaranteed cleanup hook to prevent leaving touchpad unresponsive."""
        self._set_device_grab(False)
        if self._fd is not None:
            with contextlib.suppress(OSError):
                os.close(self._fd)
            self._fd = None
        if self._uinput is not None:
            self._uinput.close()
            self._uinput = None

    def _handle_signal(self, signum: int, _frame: FrameType | None) -> None:
        """Handle termination signals safely."""
        self.logger.info("Received signal %d, cleanly exiting...", signum)
        self._running = False

    def run(
        self,
        max_duration: float = 0.0,
        event_callback: Callable[[Zone, int, int], None] | None = None,
    ) -> None:
        """Main event loop processing evdev input."""
        # Register fail-safe cleanup with atexit and signal handlers
        atexit.register(self._cleanup)
        for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(sig, self._handle_signal)

        self.logger.info("Listening on %s (%s)", self.touchpad.path, self.touchpad.name)
        self.logger.info(
            "Geometry: X:[%d..%d] Y:[%d..%d] | edge_x=%dpx, bottom_limit=%dpx, step=%dpx",
            self.touchpad.x_min,
            self.touchpad.x_max,
            self.touchpad.y_min,
            self.touchpad.y_max,
            self.edge_x,
            self.bottom_limit,
            self.step_y,
        )
        if self.cfg.dry_run:
            self.logger.info("DRY RUN ENABLED - no keys will be emitted, no grabs taken.")

        try:
            self._fd = os.open(self.touchpad.path, os.O_RDONLY)
        except PermissionError as err:
            raise PermissionError(
                f"Cannot open {self.touchpad.path}: permission denied. Run as root or join input group."
            ) from err

        if not self.cfg.dry_run:
            self._uinput = UInputDevice(name="asus-smart-gestures")

        slots: dict[int, TouchSlot] = {}
        active_slot = 0
        gesture: ActiveGesture | None = None
        deadline = time.monotonic() + max_duration if max_duration > 0 else None
        self._running = True

        def emit(key: KeyCode | None) -> None:
            if key is None:
                return
            self.logger.info("  -> Emitting %s", key.name)
            if self._uinput:
                self._uinput.tap(key)

        def release_gesture() -> None:
            nonlocal gesture
            self._set_device_grab(False)
            gesture = None

        def primary_slot_id() -> int | None:
            for s in sorted(slots.keys()):
                if slots[s].tracking_id is not None:
                    return s
            return None

        try:
            while self._running:
                if deadline and time.monotonic() > deadline:
                    break

                try:
                    data = os.read(self._fd, EVENT_SIZE)
                except OSError as err:
                    if self._running:
                        self.logger.error("Read error on %s: %s", self.touchpad.path, err)
                    break

                if len(data) < EVENT_SIZE:
                    continue

                _, _, etype, code, value = struct.unpack(INPUT_EVENT_FMT, data)

                if etype == EV_ABS:
                    if code == ABS_MT_SLOT:
                        active_slot = value
                    elif code == ABS_MT_TRACKING_ID:
                        if value == -1:
                            slots.pop(active_slot, None)
                        else:
                            slots[active_slot] = TouchSlot(tracking_id=value)
                    elif code == ABS_MT_POSITION_X:
                        slots.setdefault(active_slot, TouchSlot()).x = value
                    elif code == ABS_MT_POSITION_Y:
                        slots.setdefault(active_slot, TouchSlot()).y = value

                elif etype == EV_SYN and code == SYN_REPORT:
                    cur_slot = primary_slot_id()

                    # Active finger lifted
                    if gesture is not None and gesture.slot_id not in slots:
                        release_gesture()

                    # New finger down
                    if gesture is None and cur_slot is not None:
                        slot_data = slots[cur_slot]
                        sx, sy = slot_data.x, slot_data.y
                        zone = self._determine_zone(sx, sy)

                        if event_callback:
                            event_callback(zone, sx, sy)

                        if zone != Zone.NONE:
                            self.logger.info(
                                "Touch start at (%d, %d) -> [%s EDGE]",
                                sx,
                                sy,
                                zone.value.upper(),
                            )
                            self._set_device_grab(True)
                            gesture = ActiveGesture(
                                zone=zone,
                                slot_id=cur_slot,
                                step_ref_y=sy,
                                step_ref_x=sx,
                                start_x=sx,
                                start_y=sy,
                            )

                    # Continuous movement
                    if gesture is not None and cur_slot == gesture.slot_id:
                        slot_data = slots[cur_slot]
                        cx, cy = slot_data.x, slot_data.y

                        if gesture.zone in (Zone.LEFT, Zone.RIGHT):
                            action = (
                                self.cfg.left_edge_action
                                if gesture.zone == Zone.LEFT
                                else self.cfg.right_edge_action
                            )
                            invert = (
                                self.cfg.invert_left
                                if gesture.zone == Zone.LEFT
                                else self.cfg.invert_right
                            )
                            pos_k, neg_k = self._resolve_keys(action, invert)

                            ref_y = gesture.step_ref_y
                            # Slide UP (towards 0, decreasing Y)
                            while ref_y - cy >= self.step_y:
                                emit(pos_k)
                                ref_y -= self.step_y
                            # Slide DOWN (increasing Y)
                            while cy - ref_y >= self.step_y:
                                emit(neg_k)
                                ref_y += self.step_y
                            gesture.step_ref_y = ref_y

                        elif gesture.zone == Zone.TOP:
                            pos_k, neg_k = self._resolve_keys(
                                self.cfg.top_edge_action, self.cfg.invert_top
                            )
                            ref_x = gesture.step_ref_x
                            # Slide RIGHT (increasing X)
                            while cx - ref_x >= self.step_x:
                                emit(pos_k)
                                ref_x += self.step_x
                            # Slide LEFT (decreasing X)
                            while ref_x - cx >= self.step_x:
                                emit(neg_k)
                                ref_x -= self.step_x
                            gesture.step_ref_x = ref_x

        except KeyboardInterrupt:
            self.logger.info("Exiting cleanly on KeyboardInterrupt")
        finally:
            self._cleanup()
            atexit.unregister(self._cleanup)
