"""Main gesture daemon tracking touches, zones, and emitting events."""

import fcntl
import os
import struct
import time
from typing import Callable, Dict, Optional, Tuple

from .config import GestureConfig
from .uinput import (
    KEY_BRIGHTNESSDOWN,
    KEY_BRIGHTNESSUP,
    KEY_NAMES,
    KEY_NEXTSONG,
    KEY_PREVIOUSSONG,
    KEY_VOLUMEDOWN,
    KEY_VOLUMEUP,
    UInputDevice,
)

FMT = "llHHi"
SZ = struct.calcsize(FMT)

EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03
SYN_REPORT = 0x00

BTN_TOUCH = 0x14A
ABS_MT_SLOT = 0x2F
ABS_MT_POSITION_X = 0x35
ABS_MT_POSITION_Y = 0x36
ABS_MT_TRACKING_ID = 0x39

EVIOCGRAB = 0x40044590


class GestureDaemon:
    """Manages raw evdev stream from touchpad and translates edge slides to keys."""

    def __init__(
        self,
        device_path: str,
        device_name: str,
        x_range: Tuple[int, int],
        y_range: Tuple[int, int],
        config: GestureConfig,
    ):
        self.device_path = device_path
        self.device_name = device_name
        self.x_min, self.x_max = x_range
        self.y_min, self.y_max = y_range
        self.cfg = config

        # Pad coordinate dimensions
        width = self.x_max - self.x_min
        height = self.y_max - self.y_min

        # Calculated pixel thresholds based on config percentages
        self.edge_x = max(1, int((self.cfg.edge_x_percent / 100.0) * width))
        self.bottom_limit = self.y_max - int((self.cfg.bottom_ignore_percent / 100.0) * height)
        self.step_y = max(1, int((self.cfg.step_travel_percent / 100.0) * height))

        self.top_limit = self.y_min + int((self.cfg.top_edge_percent / 100.0) * height)
        self.step_x = max(1, int((self.cfg.top_step_travel_percent / 100.0) * width))

        self.uinput: Optional[UInputDevice] = None
        if not self.cfg.dry_run:
            self.uinput = UInputDevice(name="asus-smart-gestures")

    def _determine_zone(self, x: int, y: int) -> Optional[str]:
        # Exclude bottom clickpad area
        if y > self.bottom_limit:
            return None

        # Check top horizontal zone if enabled
        if self.cfg.enable_top_edge and y < self.top_limit:
            # If not in the left/right corner strips, it's top
            if x >= (self.x_min + self.edge_x) and x <= (self.x_max - self.edge_x):
                return "top"

        # Check left / right vertical zones
        if x < (self.x_min + self.edge_x):
            return "left"
        if x > (self.x_max - self.edge_x):
            return "right"

        return None

    def _resolve_keys_for_action(self, action: str, invert: bool) -> Tuple[Optional[int], Optional[int]]:
        """Return (positive_key, negative_key) for an action."""
        pos, neg = None, None
        if action == "volume":
            pos, neg = KEY_VOLUMEUP, KEY_VOLUMEDOWN
        elif action == "brightness":
            pos, neg = KEY_BRIGHTNESSUP, KEY_BRIGHTNESSDOWN
        elif action == "media":
            pos, neg = KEY_NEXTSONG, KEY_PREVIOUSSONG

        if invert and pos is not None and neg is not None:
            return neg, pos
        return pos, neg

    def run(self, max_duration: float = 0.0, event_callback: Optional[Callable[[str, int, int], None]] = None) -> None:
        """Main event polling loop."""
        fd = os.open(self.device_path, os.O_RDONLY)
        deadline = time.monotonic() + max_duration if max_duration > 0 else None

        slots: Dict[int, Dict[str, any]] = {}
        active_slot = 0
        track: Optional[Dict[str, any]] = None
        tracked_slot: Optional[int] = None
        grabbed = False

        def emit(code: Optional[int]) -> None:
            if code is None:
                return
            name = KEY_NAMES.get(code, f"KEY_{code}")
            print(f"  -> {name}", flush=True)
            if self.uinput:
                self.uinput.tap(code)

        def release_track():
            nonlocal track, tracked_slot, grabbed
            if grabbed:
                try:
                    fcntl.ioctl(fd, EVIOCGRAB, 0)
                except OSError:
                    pass
                grabbed = False
            track = None
            tracked_slot = None

        def primary_slot() -> Optional[int]:
            for s in sorted(slots.keys()):
                if slots[s].get("id") is not None:
                    return s
            return None

        print(
            f"asus-smart-gestures: listening on {self.device_path} ({self.device_name})\n"
            f"  bounds X:[{self.x_min}..{self.x_max}] Y:[{self.y_min}..{self.y_max}] "
            f"edge_x={self.edge_x} bottom_limit={self.bottom_limit} step_y={self.step_y}"
            f"{' [DRY RUN]' if self.cfg.dry_run else ''}",
            flush=True,
        )

        try:
            while True:
                if deadline and time.monotonic() > deadline:
                    break

                data = os.read(fd, SZ)
                if len(data) < SZ:
                    continue
                _, _, etype, code, value = struct.unpack(FMT, data)

                if etype == EV_ABS:
                    if code == ABS_MT_SLOT:
                        active_slot = value
                    elif code == ABS_MT_TRACKING_ID:
                        if value == -1:
                            slots.pop(active_slot, None)
                        else:
                            slots[active_slot] = {"id": value, "x": 0, "y": 0}
                    elif code == ABS_MT_POSITION_X:
                        slots.setdefault(active_slot, {"id": None, "x": 0, "y": 0})["x"] = value
                    elif code == ABS_MT_POSITION_Y:
                        slots.setdefault(active_slot, {"id": None, "x": 0, "y": 0})["y"] = value

                elif etype == EV_SYN and code == SYN_REPORT:
                    cur = primary_slot()

                    # Finger lifted
                    if track is not None and tracked_slot not in slots:
                        release_track()

                    # New finger down
                    if track is None and cur is not None:
                        sx = slots[cur].get("x", 0)
                        sy = slots[cur].get("y", 0)
                        tracked_slot = cur
                        zone = self._determine_zone(sx, sy)

                        if event_callback:
                            event_callback(zone or "center", sx, sy)

                        track = {
                            "zone": zone,
                            "step_ref_y": sy,
                            "step_ref_x": sx,
                            "start_x": sx,
                            "start_y": sy,
                        }

                        if zone:
                            print(f"touch start ({sx}, {sy}) -> {zone}", flush=True)
                            if not self.cfg.dry_run and not grabbed:
                                try:
                                    fcntl.ioctl(fd, EVIOCGRAB, 1)
                                    grabbed = True
                                except OSError:
                                    pass

                    # Movement in progress
                    if track is not None and cur == tracked_slot:
                        x = slots[cur].get("x", 0)
                        y = slots[cur].get("y", 0)
                        zone = track["zone"]

                        if zone in ("left", "right"):
                            action = self.cfg.left_edge_action if zone == "left" else self.cfg.right_edge_action
                            invert = self.cfg.invert_left if zone == "left" else self.cfg.invert_right
                            pos_key, neg_key = self._resolve_keys_for_action(action, invert)

                            ref_y = track["step_ref_y"]
                            # Finger moving UP (decreasing Y)
                            while ref_y - y >= self.step_y:
                                emit(pos_key)
                                ref_y -= self.step_y
                            # Finger moving DOWN (increasing Y)
                            while y - ref_y >= self.step_y:
                                emit(neg_key)
                                ref_y += self.step_y
                            track["step_ref_y"] = ref_y

                        elif zone == "top":
                            action = self.cfg.top_edge_action
                            invert = self.cfg.invert_top
                            pos_key, neg_key = self._resolve_keys_for_action(action, invert)

                            ref_x = track["step_ref_x"]
                            # Finger moving RIGHT (increasing X)
                            while x - ref_x >= self.step_x:
                                emit(pos_key)
                                ref_x += self.step_x
                            # Finger moving LEFT (decreasing X)
                            while ref_x - x >= self.step_x:
                                emit(neg_key)
                                ref_x -= self.step_x
                            track["step_ref_x"] = ref_x

        except KeyboardInterrupt:
            pass
        finally:
            release_track()
            os.close(fd)
            if self.uinput:
                self.uinput.close()
