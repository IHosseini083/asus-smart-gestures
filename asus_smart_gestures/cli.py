"""CLI entry point and command router for asus-smart-gestures."""

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import load_config
from .constants import Zone
from .daemon import GestureDaemon
from .detector import find_touchpad, scan_touchpads
from .diagnostics import run_doctor
from .logging import get_logger, setup_logging


def run_calibrate(daemon: GestureDaemon, duration: float = 30.0) -> None:
    """Run interactive calibration displaying touch coordinates and zone boundaries."""
    tp = daemon.touchpad
    print("=" * 70)
    print(" ASUS Smart Gestures - Interactive Calibration Visualizer")
    print("=" * 70)
    print(f" Touchpad Device : {tp.name} ({tp.path})")
    print(f" Coordinates     : X:[{tp.x_min}..{tp.x_max}] (width={tp.width}px)")
    print(f"                   Y:[{tp.y_min}..{tp.y_max}] (height={tp.height}px)")
    print("-" * 70)
    print(
        f" Left Edge Strip : X < {tp.x_min + daemon.edge_x}  (first {daemon.cfg.edge_x_percent:.1f}%)"
    )
    print(
        f" Right Edge Strip: X > {tp.x_max - daemon.edge_x}  (last {daemon.cfg.edge_x_percent:.1f}%)"
    )
    if daemon.cfg.enable_top_edge:
        print(
            f" Top Edge Strip  : Y < {daemon.top_limit}  (top {daemon.cfg.top_edge_percent:.1f}%)"
        )
    else:
        print(" Top Edge Strip  : [DISABLED] (set enable_top_edge = true to enable)")
    print(f" Bottom Ignore   : Y > {daemon.bottom_limit} (clickpad exclusion)")
    print("=" * 70)
    print("Touch and slide along the trackpad edges. Press Ctrl+C to stop.\n")

    def on_touch(zone: Zone, x: int, y: int) -> None:
        x_pct = ((x - tp.x_min) / tp.width) * 100.0 if tp.width > 0 else 0.0
        y_pct = ((y - tp.y_min) / tp.height) * 100.0 if tp.height > 0 else 0.0

        if zone == Zone.LEFT:
            tag = "\033[34m[LEFT EDGE - VOLUME]\033[0m"
        elif zone == Zone.RIGHT:
            tag = "\033[33m[RIGHT EDGE - BRIGHTNESS]\033[0m"
        elif zone == Zone.TOP:
            tag = "\033[35m[TOP EDGE - MEDIA]\033[0m"
        else:
            tag = "\033[90m[CENTER - NORMAL CURSOR]\033[0m"

        print(f" Touch at ({x:5d}, {y:5d}) | {x_pct:4.1f}% X, {y_pct:4.1f}% Y  -->  {tag}")

    daemon.run(max_duration=duration, event_callback=on_touch)


def main() -> None:
    """Parse command line arguments and execute the appropriate handler."""
    parser = argparse.ArgumentParser(
        prog="asus-smart-gestures",
        description="ASUS touchpad edge-slide gesture daemon for Linux (volume, brightness, media).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-c", "--config", type=Path, help="Path to custom configuration file")
    parser.add_argument(
        "-d",
        "--device",
        type=Path,
        help="Path to specific evdev input device (e.g. /dev/input/event10)",
    )
    parser.add_argument(
        "--dry",
        action="store_true",
        help="Dry run: monitor gestures without capturing device or emitting keys",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Scan and list all multitouch touchpads detected on this machine",
    )
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="Interactive visual tool to test edge thresholds",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Audit system environment and report hardware/privilege health",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress informational messages"
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run for N seconds then exit (useful for testing and CI)",
    )

    args = parser.parse_args()

    # Configure logger before running tasks
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    logger = get_logger()

    if args.doctor:
        healthy = run_doctor()
        sys.exit(0 if healthy else 1)

    if args.scan:
        touchpads = scan_touchpads()
        if not touchpads:
            print("No multitouch touchpads detected in /dev/input (try with sudo).")
            sys.exit(1)
        print(f"Detected {len(touchpads)} multitouch touchpad(s):")
        for i, tp in enumerate(touchpads, 1):
            print(f"[{i}] {tp.name}")
            print(f"    Path       : {tp.path}")
            print(
                f"    Resolution : {tp.width}x{tp.height} (X:[{tp.x_min}..{tp.x_max}], Y:[{tp.y_min}..{tp.y_max}])"
            )
        sys.exit(0)

    cfg = load_config(args.config)
    if args.dry:
        cfg.dry_run = True
    if args.device:
        cfg.device = str(args.device)

    try:
        touchpad = find_touchpad(cfg.device)
    except (RuntimeError, ValueError) as err:
        logger.error("Initialization error: %s", err)
        sys.exit(1)

    daemon = GestureDaemon(touchpad=touchpad, config=cfg)

    if args.calibrate:
        cfg.dry_run = True
        run_calibrate(daemon, duration=args.duration if args.duration > 0 else 60.0)
    else:
        try:
            daemon.run(max_duration=args.duration)
        except PermissionError as err:
            logger.error("%s", err)
            sys.exit(1)


if __name__ == "__main__":
    main()
