#!/usr/bin/env python3
"""
stay_active.py — Prevents system sleep and keeps you showing as active.

How it works:
  1. Runs `caffeinate -i` to prevent idle system sleep.
  2. Nudges the mouse by a small random amount every N seconds so the OS
     never registers an idle period.

Usage:
  python3 stay_active.py                          # default 30-second nudge interval
  python3 stay_active.py --interval 60            # plain seconds
  python3 stay_active.py --interval 2m            # 2 minutes
  python3 stay_active.py --human --duration 1.5h  # human mode for 1.5 hours
"""

import subprocess
import sys
import time
import signal
import threading
import argparse
import random
from datetime import datetime

import re


def parse_duration(value: str) -> int:
    """
    Parse a human-readable duration string into whole seconds.
    Accepts: plain integers ("90"), seconds ("90s"), minutes ("15m"),
             hours ("2h"), and decimals ("1.5h", "0.5m").
    """
    value = value.strip()
    match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*([smh]?)", value, re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid duration '{value}'. Use formats like: 30, 30s, 15m, 1h, 1.5h"
        )
    amount, unit = float(match.group(1)), match.group(2).lower()
    multiplier = {"s": 1, "m": 60, "h": 3600, "": 1}[unit]
    return max(1, int(amount * multiplier))


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
        CGMainDisplayID,
        CGDisplayBounds,
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


def get_screen_size() -> tuple:
    """Return (width, height) of the main display in points."""
    bounds = CGDisplayBounds(CGMainDisplayID())
    return bounds.size.width, bounds.size.height


def _bezier(p0, p1, p2, t: float) -> tuple:
    """Quadratic Bezier point at parameter t in [0, 1]."""
    u = 1 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]
    return x, y


def _ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def human_nudge(screen_w: float, screen_h: float) -> tuple:
    """
    Move the mouse to a random screen location along a Bezier curve with
    variable speed, micro-jitter, and irregular pauses — indistinguishable
    from organic hand movement.

    Returns (success, idle_before, idle_after).
    """
    ox, oy = get_mouse_position()

    # Random destination anywhere on screen with a small margin
    margin = 60
    tx = random.uniform(margin, screen_w - margin)
    ty = random.uniform(margin, screen_h - margin)

    # Off-axis control point creates a natural curve (not a straight line)
    cx = random.uniform(
        min(ox, tx) - random.uniform(50, 200),
        max(ox, tx) + random.uniform(50, 200),
    )
    cy = random.uniform(
        min(oy, ty) - random.uniform(50, 200),
        max(oy, ty) + random.uniform(50, 200),
    )

    # Scale step count with distance so speed feels consistent
    dist = ((tx - ox) ** 2 + (ty - oy) ** 2) ** 0.5
    steps = int(random.uniform(25, 55) * max(dist / 600, 0.4))
    steps = max(18, min(steps, 90))

    idle_before = get_idle_seconds()

    for i in range(steps + 1):
        t = i / steps
        et = _ease_in_out(t)

        # Gaussian micro-jitter — small, asymmetric, non-uniform
        jx = random.gauss(0, random.uniform(0.3, 1.2))
        jy = random.gauss(0, random.uniform(0.3, 1.2))

        x, y = _bezier((ox, oy), (cx, cy), (tx, ty), et)
        post_mouse_move(x + jx, y + jy)

        # Speed profile: slower at start/end, faster through the arc
        # Occasional micro-stutter simulates finger/wrist hesitation
        base_delay = random.uniform(0.007, 0.022)
        edge_factor = 1.0 + 1.2 * (1 - abs(2 * t - 1))  # peaks at t=0 and t=1
        if random.random() < 0.06:          # ~6% chance of a tiny stutter
            base_delay += random.uniform(0.03, 0.09)
        time.sleep(base_delay * edge_factor)

    # Natural pause after arriving — humans don't instantly move away
    time.sleep(random.uniform(0.15, 0.55))

    time.sleep(0.3)  # let IOKit reflect before sampling
    idle_after = get_idle_seconds()

    if idle_before < 0 or idle_after < 0:
        return None, idle_before, idle_after
    return idle_after < idle_before, idle_before, idle_after


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


def fmt_seconds(secs: int) -> str:
    """Format a whole number of seconds as a compact human-readable string."""
    h, rem = divmod(int(secs), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h {m:02d}m {s:02d}s"
    if m:
        return f"{m}m {s:02d}s"
    return f"{s}s"


def activity_loop(stop_event: threading.Event, interval: int, human: bool,
                  start_time: float, duration: int | None):
    nudge_count = 0
    screen_w, screen_h = get_screen_size() if human else (0, 0)

    while not stop_event.wait(interval):
        if human:
            success, idle_before, idle_after = human_nudge(screen_w, screen_h)
        else:
            success, idle_before, idle_after = nudge()
        nudge_count += 1
        ts = datetime.now().strftime("%H:%M:%S")
        mode = "human" if human else "nudge"
        elapsed = time.monotonic() - start_time

        if duration:
            remaining = max(0, duration - elapsed)
            time_info = f"left {fmt_seconds(remaining)}"
        else:
            time_info = f"runtime {fmt_seconds(elapsed)}"

        if success is None:
            print(f"  [{ts}] {mode} #{nudge_count}  {time_info} — idle time unavailable", flush=True)
        elif success:
            print(f"  [{ts}] {mode} #{nudge_count}  {time_info} — idle {idle_before:.1f}s → {idle_after:.1f}s  [OK]", flush=True)
        else:
            print(f"  [{ts}] {mode} #{nudge_count}  {time_info} — idle {idle_before:.1f}s → {idle_after:.1f}s  [FAILED — check Accessibility permission]", flush=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Keep system awake and you showing as active.")
    parser.add_argument(
        "--interval",
        type=parse_duration,
        default=30,
        metavar="TIME",
        help="Time between nudges — e.g. 30, 30s, 5m, 1h (default: 30s)",
    )
    parser.add_argument(
        "--human",
        action="store_true",
        help="Move mouse naturally across the full screen (Bezier path, variable speed, jitter)",
    )
    parser.add_argument(
        "--duration",
        type=parse_duration,
        default=None,
        metavar="TIME",
        help="Auto-stop after this long — e.g. 3600, 30m, 2h, 1.5h (default: indefinite)",
    )
    args = parser.parse_args()

    mode_label = "human (Bezier)" if args.human else "nudge (small offset)"
    duration_label = fmt_seconds(args.duration) if args.duration else "indefinite"
    interval_label = fmt_seconds(args.interval)
    started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 52)
    print("  stay_active — system awake + staying active")
    print("=" * 52)
    print(f"  Started        : {started_at}")
    print(f"  Mode           : {mode_label}")
    print(f"  Nudge interval : {interval_label}")
    print(f"  Duration       : {duration_label}")
    print("  Press Ctrl+C to stop.")
    print("-" * 52)

    print("  Checking Accessibility permission...", end=" ", flush=True)
    check_accessibility()
    print("OK")

    caffeinate_proc = start_caffeinate()
    print(f"  caffeinate PID : {caffeinate_proc.pid}")
    print("-" * 52)

    start_time = time.monotonic()
    stop_event = threading.Event()
    thread = threading.Thread(
        target=activity_loop,
        args=(stop_event, args.interval, args.human, start_time, args.duration),
        daemon=True,
    )
    thread.start()

    def shutdown(sig, frame):
        elapsed = time.monotonic() - start_time
        print("\n" + "-" * 52)
        print(f"  Stopping — ran for {fmt_seconds(elapsed)}. Sleep restored.")
        stop_event.set()
        caffeinate_proc.terminate()
        caffeinate_proc.wait()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Keep the main thread alive; honour --duration if set.
    if args.duration:
        stop_event.wait(args.duration)
        shutdown(None, None)
    else:
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
