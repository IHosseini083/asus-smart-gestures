"""Unit tests for touchpad detector and security path sanitization."""

from pathlib import Path

import pytest

from asus_smart_gestures.detector import (
    TouchpadInfo,
    _has_bit,
    validate_device_path,
)


def test_touchpad_info_properties() -> None:
    """Test resolution calculations on TouchpadInfo."""
    tp = TouchpadInfo(
        path=Path("/dev/input/event10"),
        name="ASUS Touchpad",
        x_min=0,
        x_max=4000,
        y_min=0,
        y_max=2500,
    )
    assert tp.width == 4000
    assert tp.height == 2500


def test_has_bit_helper() -> None:
    """Test bitfield parsing helper."""
    buf = bytearray([0b00000001, 0b10000000])  # bit 0 and bit 15 set
    assert _has_bit(buf, 0) is True
    assert _has_bit(buf, 1) is False
    assert _has_bit(buf, 15) is True
    assert _has_bit(buf, 16) is False
    assert _has_bit(buf, 999) is False


def test_validate_device_path_rejects_nonexistent() -> None:
    """Test that nonexistent paths raise ValueError."""
    with pytest.raises(ValueError, match="does not exist"):
        validate_device_path("/dev/input/nonexistent_device_xyz")


def test_validate_device_path_rejects_regular_file(tmp_path: Path) -> None:
    """Test that regular files (not character devices) are rejected."""
    fake_file = tmp_path / "event0"
    fake_file.write_text("not a char dev")
    with pytest.raises(ValueError, match="not a character device"):
        validate_device_path(fake_file)
