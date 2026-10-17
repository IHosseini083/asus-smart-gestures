"""Unit tests for daemon zone determination and key mapping."""

from pathlib import Path

import pytest

from asus_smart_gestures.config import GestureConfig
from asus_smart_gestures.constants import Action, KeyCode, Zone
from asus_smart_gestures.daemon import GestureDaemon
from asus_smart_gestures.detector import TouchpadInfo


@pytest.fixture
def mock_touchpad() -> TouchpadInfo:
    """Fixture returning a standard 4000x2500 virtual touchpad geometry."""
    return TouchpadInfo(
        path=Path("/dev/input/event0"),
        name="Mock ASUS Trackpad",
        x_min=0,
        x_max=4000,
        y_min=0,
        y_max=2500,
    )


def test_zone_determination(mock_touchpad: TouchpadInfo) -> None:
    """Verify coordinate classification into edge zones."""
    cfg = GestureConfig(
        edge_x_percent=10.0,  # 400px left/right
        bottom_ignore_percent=20.0,  # bottom 500px ignored (y > 2000)
        enable_top_edge=True,
        top_edge_percent=10.0,  # top 250px (y < 250)
    )
    daemon = GestureDaemon(touchpad=mock_touchpad, config=cfg)

    # Left edge
    assert daemon._determine_zone(150, 1000) == Zone.LEFT
    assert daemon._determine_zone(399, 1000) == Zone.LEFT

    # Right edge
    assert daemon._determine_zone(3601, 1000) == Zone.RIGHT
    assert daemon._determine_zone(3900, 1000) == Zone.RIGHT

    # Top edge
    assert daemon._determine_zone(2000, 100) == Zone.TOP

    # Center
    assert daemon._determine_zone(2000, 1000) == Zone.NONE

    # Bottom ignored zone (clickpad)
    assert daemon._determine_zone(100, 2200) == Zone.NONE
    assert daemon._determine_zone(3900, 2200) == Zone.NONE
    assert daemon._determine_zone(2000, 2200) == Zone.NONE


def test_key_mapping_resolution(mock_touchpad: TouchpadInfo) -> None:
    """Test resolution of keycodes and inversion behavior."""
    daemon = GestureDaemon(touchpad=mock_touchpad, config=GestureConfig())

    # Standard volume
    pos, neg = daemon._resolve_keys(Action.VOLUME, invert=False)
    assert pos == KeyCode.VOLUMEUP
    assert neg == KeyCode.VOLUMEDOWN

    # Inverted volume
    pos_inv, neg_inv = daemon._resolve_keys(Action.VOLUME, invert=True)
    assert pos_inv == KeyCode.VOLUMEDOWN
    assert neg_inv == KeyCode.VOLUMEUP

    # Standard brightness
    pos_b, neg_b = daemon._resolve_keys(Action.BRIGHTNESS, invert=False)
    assert pos_b == KeyCode.BRIGHTNESSUP
    assert neg_b == KeyCode.BRIGHTNESSDOWN

    # Media
    pos_m, neg_m = daemon._resolve_keys(Action.MEDIA, invert=False)
    assert pos_m == KeyCode.NEXTSONG
    assert neg_m == KeyCode.PREVIOUSSONG

    # Action NONE
    pos_none, neg_none = daemon._resolve_keys(Action.NONE, invert=False)
    assert pos_none is None
    assert neg_none is None
