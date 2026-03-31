# stay_active

Keeps your Mac awake and your status showing as **active** — even when you step away.

## The problem

`caffeinate` prevents your Mac from sleeping, but apps monitor a separate idle timer (`CGEventSourceSecondsSinceLastEventType`) to flip your status to "away". Simply preventing sleep doesn't reset that timer.

## How it works

| Mechanism | What it does |
|---|---|
| `caffeinate -i` | Prevents idle system sleep; display can still sleep normally |
| Mouse nudge | Posts a real `CGEventMouseMoved` event every N seconds, resetting the OS idle timer |

Two nudge modes are available:

| Mode | Behaviour |
|---|---|
| Default | Moves cursor 3–8px in a random direction and back; cursor returns to its original position |
| `--human` | Moves cursor to a random screen location along a Bezier curve with easing, micro-jitter, and occasional stutters — indistinguishable from real hand movement |

## Requirements

- macOS (uses Quartz / CoreGraphics — built into macOS)
- Python 3 (pre-installed on macOS)

## Setup & run

```bash
./run.sh
```

That's it. `run.sh` automatically creates the venv and installs dependencies if needed, then starts the script. All arguments pass through:

```bash
./run.sh --human                          # human-like Bezier movement
./run.sh --interval 60                    # nudge every 60s (default: 30s)
./run.sh --duration 3600                  # stop after 1 hour (default: indefinite)
./run.sh --human --interval 60 --duration 7200
```

Press `Ctrl+C` to stop. `caffeinate` is cleanly terminated and normal sleep behaviour is restored.

### Manual setup (alternative)

```bash
bash setup.sh
venv/bin/python3 stay_active.py --human
```

### Accessibility permission

The script posts synthetic mouse events, which requires **Accessibility** permission for your terminal app (Terminal, iTerm2, etc.).

On first run the script checks this automatically. If permission is missing it opens **System Settings → Privacy & Security → Accessibility** for you.

To grant it manually:
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+** and add your terminal app
3. Enable the toggle next to it
4. Re-run the script

## Options

| Flag | Default | Description |
|---|---|---|
| `--human` | off | Human-like Bezier movement across the full screen |
| `--interval SEC` | `30` | Seconds between nudges |
| `--duration SEC` | indefinite | Auto-stop after this many seconds |

## Output

```
==================================================
  stay_active — system awake + staying active
==================================================
  Mode           : human (Bezier)
  Nudge interval : every 30s
  Duration       : until Ctrl+C
  Press Ctrl+C to stop.
--------------------------------------------------
  Checking Accessibility permission... OK
  caffeinate PID : 12345
  [09:46:29] human #1 — idle 30.3s → 0.1s  [OK]
  [09:47:00] human #2 — idle 30.2s → 0.1s  [OK]
```

| Status | Meaning |
|---|---|
| `[OK]` | Idle timer was reset successfully |
| `[FAILED]` | Timer did not reset — check Accessibility permission |

## Files

```
run.sh            # entry point — use this to run the script
stay_active.py    # main script
setup.sh          # one-shot venv setup
requirements.txt  # Python dependencies
venv/             # created by setup — not committed
```
