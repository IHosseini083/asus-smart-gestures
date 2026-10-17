"""CLI entry point for asus-smart-gestures."""

import argparse
import sys
import time

from . import __version__
from .config import load_config
from .daemon import GestureDaemon
from .detector import find_best_touchpad, scan_touchpads


def run_calibrate(daemon: GestureDaemon, duration: float = 30.0) -> None:
    """Live visual calibration displaying touch coordinates and zone matching."""
    print("=" * 65)
    print(" ASUS Smart Gestures - Calibration Mode")
    print(f" Touchpad: {daemon.device_name} ({daemon.device_path})")
    print(f" Coordinate Extents: X:[{daemon.x_min}..{daemon.x_max}] Y:[{daemon.y_min}..{daemon.y_max}]")
    print(f" Left Edge Strip : X < {daemon.x_min + daemon.edge_x}")
    print(f" Right Edge Strip: X > {daemon.x_max - daemon.edge_x}")
    print(f" Top Edge Strip  : Y < {daemon.top_limit} (enabled={daemon.cfg.enable_top_edge})")
    print(f" Bottom Ignore   : Y > {daemon.bottom_limit} (clickpad)")
    print("=" * 65)
    print("Slide your finger along the edges to test. Press Ctrl+C to exit.\n")

    def on_touch(zone: str, x: int, y: int):
        x_pct = ((x - daemon.x_min) / (daemon.x_max - daemon.x_min)) * 100.0
        y_pct = ((y - daemon.y_min) / (daemon.y_max - daemon.y_min)) * 100.0
        tag = f"[{zone.upper()}]" if zone != "center" else "[CENTER (IGNORED)]"
        print(f"Touch at ({x:5d}, {y:5d}) | {x_pct:4.1f}% X, {y_pct:4.1f}% Y  -->  {tag}")

    daemon.run(max_duration=duration, event_callback=on_touch)


def main():
    parser = argparse.ArgumentParser(
        prog="asus-smart-gestures",
        description="ASUS touchpad edge-slide gesture daemon for Linux.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-c", "--config", help="Path to custom configuration file")
    parser.add_argument("-d", "--device", help="Path to evdev input device (e.g. /dev/input/event10)")
    parser.add_argument("--dry", action="store_true", help="Dry run: trace gestures without capturing device or emitting keys")
    parser.add_argument("--scan", action="store_true", help="Scan and list all detected touchpads on this machine")
    parser.add_argument("--calibrate", action="store_true", help="Interactive calibration tool to test edge thresholds")
    parser.add_argument("--duration", type=float, default=0.0, help="Exit after N seconds (useful for testing)")

    args = parser.parse_args()

    if args.scan:
        print("Scanning for multitouch touchpads...")
        touchpads = scan_touchpads()
        if not touchpads:
            print("No multitouch touchpads detected.")
            sys.exit(1)
        for i, tp in enumerate(touchpads, 1):
            print(f"[{i}] {tp['path']} - {tp['name']}")
            print(f"    X range: {tp['x_range'][0]}..{tp['x_range'][1]}")
            print(f"    Y range: {tp['y_range'][0]}..{tp['y_range'][1]}")
        sys.exit(0)

    cfg = load_config(args.config)
    if args.dry:
        cfg.dry_run = True
    if args.device:
        cfg.device = args.device

    try:
        dev_path, dev_name, x_range, y_range = find_best_touchpad(cfg.device)
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    daemon = GestureDaemon(
        device_path=dev_path,
        device_name=dev_name,
        x_range=x_range,
        y_range=y_range,
        config=cfg,
    )

    if args.calibrate:
        cfg.dry_run = True
        run_calibrate(daemon, duration=args.duration if args.duration > 0 else 60.0)
    else:
        daemon.run(max_duration=args.duration)


if __name__ == "__main__":
    main()
