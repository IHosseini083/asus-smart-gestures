"""Configuration loader, validator, and data structures."""

import configparser
from dataclasses import dataclass
from pathlib import Path

from .constants import Action
from .logging import get_logger

DEFAULT_SYSTEM_CONFIG = Path("/etc/asus-smart-gestures.conf")
DEFAULT_USER_CONFIG = Path.home() / ".config" / "asus-smart-gestures" / "config.conf"


@dataclass(slots=True)
class GestureConfig:
    """Validated runtime configuration for asus-smart-gestures."""

    device: str | None = None
    dry_run: bool = False
    log_level: str = "INFO"

    # Zone geometry (percentages of total width/height)
    edge_x_percent: float = 7.0
    bottom_ignore_percent: float = 15.0
    step_travel_percent: float = 4.0

    enable_top_edge: bool = False
    top_edge_percent: float = 8.0
    top_step_travel_percent: float = 5.0

    # Actions: Action.VOLUME, Action.BRIGHTNESS, Action.MEDIA, Action.NONE
    left_edge_action: Action = Action.VOLUME
    right_edge_action: Action = Action.BRIGHTNESS
    top_edge_action: Action = Action.MEDIA

    invert_left: bool = False
    invert_right: bool = False
    invert_top: bool = False

    def validate(self) -> None:
        """Validate percentage values and constraints."""
        if not (1.0 <= self.edge_x_percent <= 40.0):
            raise ValueError(
                f"edge_x_percent must be between 1.0 and 40.0, got {self.edge_x_percent}"
            )
        if not (0.0 <= self.bottom_ignore_percent <= 50.0):
            raise ValueError(
                f"bottom_ignore_percent must be between 0.0 and 50.0, got {self.bottom_ignore_percent}"
            )
        if not (0.5 <= self.step_travel_percent <= 30.0):
            raise ValueError(
                f"step_travel_percent must be between 0.5 and 30.0, got {self.step_travel_percent}"
            )
        if not (1.0 <= self.top_edge_percent <= 40.0):
            raise ValueError(
                f"top_edge_percent must be between 1.0 and 40.0, got {self.top_edge_percent}"
            )
        if not (0.5 <= self.top_step_travel_percent <= 30.0):
            raise ValueError(
                f"top_step_travel_percent must be between 0.5 and 30.0, got {self.top_step_travel_percent}"
            )


def _parse_action(val: str, default: Action) -> Action:
    val_clean = val.strip().lower()
    try:
        return Action(val_clean)
    except ValueError:
        get_logger().warning(
            "Unknown action '%s', falling back to default '%s'", val, default.value
        )
        return default


def load_config(config_path: Path | str | None = None) -> GestureConfig:
    """Load configuration from file or default locations.

    Args:
        config_path: Optional explicit path to configuration file.

    Returns:
        GestureConfig instance populated from file or defaults.
    """
    logger = get_logger()
    cfg = GestureConfig()
    parser = configparser.ConfigParser()

    path_to_load: Path | None = None
    if config_path:
        p = Path(config_path)
        if p.is_file():
            path_to_load = p
        else:
            logger.warning("Specified config path does not exist: %s", config_path)
    else:
        for candidate in (DEFAULT_SYSTEM_CONFIG, DEFAULT_USER_CONFIG):
            if candidate.is_file():
                path_to_load = candidate
                break

    if path_to_load:
        logger.debug("Loading configuration from %s", path_to_load)
        try:
            parser.read(path_to_load)
        except configparser.Error as err:
            logger.error("Failed to parse config file %s: %s", path_to_load, err)
            return cfg

        if "general" in parser:
            gen = parser["general"]
            dev_str = gen.get("device", fallback="").strip()
            cfg.device = dev_str if dev_str else None
            cfg.dry_run = gen.getboolean("dry_run", fallback=cfg.dry_run)
            cfg.log_level = gen.get("log_level", fallback=cfg.log_level).upper()

        if "zones" in parser:
            zones = parser["zones"]
            cfg.edge_x_percent = zones.getfloat("edge_x_percent", fallback=cfg.edge_x_percent)
            cfg.bottom_ignore_percent = zones.getfloat(
                "bottom_ignore_percent", fallback=cfg.bottom_ignore_percent
            )
            cfg.step_travel_percent = zones.getfloat(
                "step_travel_percent", fallback=cfg.step_travel_percent
            )
            cfg.enable_top_edge = zones.getboolean("enable_top_edge", fallback=cfg.enable_top_edge)
            cfg.top_edge_percent = zones.getfloat("top_edge_percent", fallback=cfg.top_edge_percent)
            cfg.top_step_travel_percent = zones.getfloat(
                "top_step_travel_percent", fallback=cfg.top_step_travel_percent
            )

        if "actions" in parser:
            act = parser["actions"]
            if "left_edge" in act:
                cfg.left_edge_action = _parse_action(act["left_edge"], Action.VOLUME)
            if "right_edge" in act:
                cfg.right_edge_action = _parse_action(act["right_edge"], Action.BRIGHTNESS)
            if "top_edge" in act:
                cfg.top_edge_action = _parse_action(act["top_edge"], Action.MEDIA)

            cfg.invert_left = act.getboolean("invert_left", fallback=cfg.invert_left)
            cfg.invert_right = act.getboolean("invert_right", fallback=cfg.invert_right)
            cfg.invert_top = act.getboolean("invert_top", fallback=cfg.invert_top)

    try:
        cfg.validate()
    except ValueError as err:
        logger.error("Invalid configuration values: %s. Using defaults.", err)
        cfg = GestureConfig()

    return cfg
