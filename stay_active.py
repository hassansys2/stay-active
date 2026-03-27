#!/usr/bin/env python3
"""
stay_active.py — Prevents system sleep and keeps you showing as active.

How it works:
  1. Runs `caffeinate -i` to prevent idle system sleep.
  2. Nudges the mouse by a small random amount every N seconds so the OS
     never registers an idle period.

Usage:
  python3 stay_active.py            # default 2-minute nudge interval
  python3 stay_active.py --interval 60   # nudge every 60 seconds
"""

import subprocess
import sys
import time
import signal
import threading
import argparse
import random
from datetime import datetime

try:
    from Quartz.CoreGraphics import (
        CGEventCreate,
        CGEventGetLocation,
        CGEventCreateMouseEvent,
        CGEventPost,
        CGPoint,
        CGEventSourceSecondsSinceLastEventType,
        kCGEventMouseMoved,
        kCGHIDEventTap,
        kCGEventSourceStateCombinedSessionState,
        kCGAnyInputEventType,
    )
except ImportError as e:
    print(f"Missing dependency: {e}. Install with:  pip install pyobjc-framework-Quartz")
    sys.exit(1)


def get_mouse_position():
    """Read the actual OS cursor position via Quartz."""
    loc = CGEventGetLocation(CGEventCreate(None))
    return (loc.x, loc.y)


def post_mouse_move(x: float, y: float):
    """Post a real CGEventMouseMoved HID event — resets HIDIdleTime reliably."""
    event = CGEventCreateMouseEvent(None, kCGEventMouseMoved, CGPoint(x, y), 0)
    CGEventPost(kCGHIDEventTap, event)

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_accessibility():
    """
    Post a test mouse event and verify HIDIdleTime actually resets.
    CGEventPost requires Accessibility permission; without it the event is
    silently dropped and the idle timer never changes.
    """
    idle_before = get_idle_seconds()
    time.sleep(1.5)  # let idle accumulate enough to detect a reset
    x, y = get_mouse_position()
    post_mouse_move(x + 1, y)
    time.sleep(0.1)
    post_mouse_move(x, y)
    time.sleep(0.3)
    idle_after = get_idle_seconds()

    if idle_after >= idle_before + 1.5:
        # idle kept growing — event was dropped
        print()
        print("  ERROR: Mouse event had no effect — Accessibility permission missing.")
        print()
        print("  Fix:")
        print("    1. Open System Settings → Privacy & Security → Accessibility")
        print("    2. Enable your terminal app (Terminal / iTerm2 / etc.)")
        print("    3. Re-run this script.")
        print()
        print("  Opening System Settings now...")
        subprocess.run(
            ["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"],
            check=False,
        )
        sys.exit(1)


def get_idle_seconds() -> float:
    """
    Read idle time via CGEventSourceSecondsSinceLastEventType.
    Returns seconds since last real or synthetic input event in the
    combined session state.
    """
    return CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType
    )


def start_caffeinate():
    """Launch caffeinate -i to prevent idle sleep while allowing display sleep."""
    return subprocess.Popen(
        ["caffeinate", "-i"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def nudge() -> tuple:
    """
    Post real CGEventMouseMoved events (not CGWarpMouseCursorPosition) so
    that HIDIdleTime reliably resets. Random offset and timing look human.

    Returns (success, idle_before, idle_after) where success is:
      True  — OS idle timer reset
      False — idle did not reset (likely missing Accessibility permission)
      None  — idle time unreadable (indeterminate)
    """
    ox, oy = get_mouse_position()
    dx = random.randint(3, 8) * random.choice([-1, 1])
    dy = random.randint(3, 8) * random.choice([-1, 1])

    idle_before = get_idle_seconds()
    post_mouse_move(ox + dx, oy + dy)
    time.sleep(random.uniform(0.1, 0.3))   # human-ish pause before returning
    post_mouse_move(ox, oy)
    time.sleep(0.3)  # allow IOKit to reflect the event before sampling
    idle_after = get_idle_seconds()

    if idle_before < 0 or idle_after < 0:
        return None, idle_before, idle_after

    return idle_after < idle_before, idle_before, idle_after


def activity_loop(stop_event: threading.Event, interval: int):
    nudge_count = 0

    while not stop_event.wait(interval):
        success, idle_before, idle_after = nudge()
        nudge_count += 1
        ts = datetime.now().strftime("%H:%M:%S")

        if success is None:
            print(f"  [{ts}] nudge #{nudge_count} — idle time unavailable", flush=True)
        elif success:
            print(f"  [{ts}] nudge #{nudge_count} — idle {idle_before:.1f}s → {idle_after:.1f}s  [OK]", flush=True)
        else:
            print(f"  [{ts}] nudge #{nudge_count} — idle {idle_before:.1f}s → {idle_after:.1f}s  [FAILED — check Accessibility permission]", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Keep system awake and you showing as active.")
    parser.add_argument(
        "--interval",
        type=int,
        default=120,
        metavar="SEC",
        help="Seconds between mouse nudges (default: 120)",
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  stay_active — system awake + staying active")
    print("=" * 50)
    print(f"  Nudge interval : every {args.interval}s")
    print("  Press Ctrl+C to stop.")
    print("-" * 50)

    print("  Checking Accessibility permission...", end=" ", flush=True)
    check_accessibility()
    print("OK")

    caffeinate_proc = start_caffeinate()
    print(f"  caffeinate PID : {caffeinate_proc.pid}")

    stop_event = threading.Event()
    thread = threading.Thread(
        target=activity_loop,
        args=(stop_event, args.interval),
        daemon=True,
    )
    thread.start()

    def shutdown(sig, frame):
        print("\n" + "-" * 50)
        print("  Stopping — restoring normal sleep behaviour.")
        stop_event.set()
        caffeinate_proc.terminate()
        caffeinate_proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep the main thread alive.
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
