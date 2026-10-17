"""Unit tests for configuration loading and validation."""

from pathlib import Path

import pytest

from asus_smart_gestures.config import GestureConfig, load_config
from asus_smart_gestures.constants import Action


def test_default_config_validation() -> None:
    """Test that default configuration passes validation."""
    cfg = GestureConfig()
    cfg.validate()
    assert cfg.edge_x_percent == 7.0
    assert cfg.bottom_ignore_percent == 15.0
    assert cfg.step_travel_percent == 4.0
    assert cfg.left_edge_action == Action.VOLUME
    assert cfg.right_edge_action == Action.BRIGHTNESS
    assert cfg.top_edge_action == Action.MEDIA
    assert not cfg.invert_left
    assert not cfg.invert_right


@pytest.mark.parametrize(
    "field,invalid_val",
    [
        ("edge_x_percent", 0.5),
        ("edge_x_percent", 45.0),
        ("bottom_ignore_percent", -1.0),
        ("bottom_ignore_percent", 55.0),
        ("step_travel_percent", 0.1),
        ("step_travel_percent", 35.0),
        ("top_edge_percent", 0.0),
        ("top_step_travel_percent", 40.0),
    ],
)
def test_invalid_config_percentages(field: str, invalid_val: float) -> None:
    """Test that out-of-range percentages raise ValueError."""
    cfg = GestureConfig()
    setattr(cfg, field, invalid_val)
    with pytest.raises(ValueError):
        cfg.validate()


def test_load_config_from_file(tmp_path: Path) -> None:
    """Test parsing an INI configuration file."""
    conf_file = tmp_path / "test.conf"
    conf_file.write_text(
        """
[general]
device = /dev/input/event5
dry_run = true
log_level = DEBUG

[zones]
edge_x_percent = 9.5
bottom_ignore_percent = 20.0
step_travel_percent = 5.0
enable_top_edge = true
top_edge_percent = 10.0
top_step_travel_percent = 6.0

[actions]
left_edge = brightness
right_edge = volume
top_edge = media
invert_left = true
invert_right = false
invert_top = true
"""
    )

    cfg = load_config(conf_file)
    assert cfg.device == "/dev/input/event5"
    assert cfg.dry_run is True
    assert cfg.log_level == "DEBUG"
    assert cfg.edge_x_percent == 9.5
    assert cfg.bottom_ignore_percent == 20.0
    assert cfg.step_travel_percent == 5.0
    assert cfg.enable_top_edge is True
    assert cfg.top_edge_percent == 10.0
    assert cfg.left_edge_action == Action.BRIGHTNESS
    assert cfg.right_edge_action == Action.VOLUME
    assert cfg.top_edge_action == Action.MEDIA
    assert cfg.invert_left is True
    assert cfg.invert_top is True


def test_load_nonexistent_config_falls_back() -> None:
    """Test loading a non-existent config path safely returns defaults."""
    cfg = load_config("/path/to/nothing/that/exists.conf")
    assert isinstance(cfg, GestureConfig)
    assert cfg.edge_x_percent == 7.0
