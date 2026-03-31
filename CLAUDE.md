# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup

```bash
bash setup.sh          # Creates venv and installs dependencies
```

Or manually:
```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

## Running

```bash
venv/bin/python3 stay_active.py                # Default 2-minute nudge interval
venv/bin/python3 stay_active.py --interval 60  # Custom interval in seconds
```

Requires macOS Accessibility permission (System Settings → Privacy & Security → Accessibility).

## Architecture

Single-file Python utility (`stay_active.py`) that solves two distinct macOS idle problems:

1. **System sleep** — prevented by spawning `caffeinate -i` as a subprocess
2. **User idle status** — `caffeinate` alone does NOT reset `CGEventSourceSecondsSinceLastEventType`, so apps still show you as "away". Solved by posting synthetic `CGEventMouseMoved` events at the HID level via `pyobjc-framework-Quartz` bindings to CoreGraphics

The nudge loop runs in a daemon thread: reads current cursor position → moves it by a random 3–8px offset → waits → returns to original position → checks the idle timer delta to verify success. Signal handlers (SIGINT, SIGTERM) cleanly terminate the `caffeinate` subprocess on exit.

## macOS-specific notes

- `CGEventPost(kCGHIDEventTap, ...)` is required (not `kCGSessionEventTap`) to reset the HID-level idle timer
- Accessibility permission check is done by posting a test event at startup and observing whether it raises
- Only dependency: `pyobjc-framework-Quartz` (CoreGraphics/Quartz bindings)
