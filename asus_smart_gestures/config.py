"""Configuration management for ASUS Smart Gestures."""

import configparser
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class GestureConfig:
    device: Optional[str] = None
    dry_run: bool = False
    log_level: str = "INFO"

    # Zone geometry (percentages of total width/height)
    edge_x_percent: float = 7.0
    bottom_ignore_percent: float = 15.0
    step_travel_percent: float = 4.0

    enable_top_edge: bool = False
    top_edge_percent: float = 8.0
    top_step_travel_percent: float = 5.0

    # Actions: "volume", "brightness", "media", "none"
    left_edge_action: str = "volume"
    right_edge_action: str = "brightness"
    top_edge_action: str = "media"

    invert_left: bool = False
    invert_right: bool = False
    invert_top: bool = False


DEFAULT_CONFIG_PATHS = [
    "/etc/asus-smart-gestures.conf",
    os.path.expanduser("~/.config/asus-smart-gestures/config.conf"),
]


def load_config(config_path: Optional[str] = None) -> GestureConfig:
    """Load configuration from file, falling back to defaults."""
    cfg = GestureConfig()
    parser = configparser.ConfigParser()

    loaded_file = None
    if config_path:
        if os.path.exists(config_path):
            parser.read(config_path)
            loaded_file = config_path
    else:
        for path in DEFAULT_CONFIG_PATHS:
            if os.path.exists(path):
                parser.read(path)
                loaded_file = path
                break

    if not loaded_file:
        return cfg

    if "general" in parser:
        gen = parser["general"]
        cfg.device = gen.get("device", fallback=None) or None
        cfg.dry_run = gen.getboolean("dry_run", fallback=cfg.dry_run)
        cfg.log_level = gen.get("log_level", fallback=cfg.log_level)

    if "zones" in parser:
        zones = parser["zones"]
        cfg.edge_x_percent = zones.getfloat("edge_x_percent", fallback=cfg.edge_x_percent)
        cfg.bottom_ignore_percent = zones.getfloat("bottom_ignore_percent", fallback=cfg.bottom_ignore_percent)
        cfg.step_travel_percent = zones.getfloat("step_travel_percent", fallback=cfg.step_travel_percent)
        cfg.enable_top_edge = zones.getboolean("enable_top_edge", fallback=cfg.enable_top_edge)
        cfg.top_edge_percent = zones.getfloat("top_edge_percent", fallback=cfg.top_edge_percent)
        cfg.top_step_travel_percent = zones.getfloat("top_step_travel_percent", fallback=cfg.top_step_travel_percent)

    if "actions" in parser:
        act = parser["actions"]
        cfg.left_edge_action = act.get("left_edge", fallback=cfg.left_edge_action).lower()
        cfg.right_edge_action = act.get("right_edge", fallback=cfg.right_edge_action).lower()
        cfg.top_edge_action = act.get("top_edge", fallback=cfg.top_edge_action).lower()
        cfg.invert_left = act.getboolean("invert_left", fallback=cfg.invert_left)
        cfg.invert_right = act.getboolean("invert_right", fallback=cfg.invert_right)
        cfg.invert_top = act.getboolean("invert_top", fallback=cfg.invert_top)

    return cfg
