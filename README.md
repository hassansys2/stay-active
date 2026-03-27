# stay_active

Keeps your Mac awake and your status showing as **active** — even when you step away.

## The problem

`caffeinate` prevents your Mac from sleeping, but apps monitor a separate idle timer (`CGEventSourceSecondsSinceLastEventType`) to flip your status to "away". Simply preventing sleep doesn't reset that timer.

## How it works

| Mechanism | What it does |
|---|---|
| `caffeinate -i` | Prevents idle system sleep; display can still sleep normally |
| Mouse nudge | Posts a real `CGEventMouseMoved` event every N seconds, resetting the OS idle timer |

The nudge moves the cursor by a small random amount (3–8px) and back. The offset and timing are randomised so it doesn't look like a robot. The cursor returns to its original position, so you won't notice it.

## Requirements

- macOS (uses Quartz / CoreGraphics — built into macOS)
- Python 3 (pre-installed on macOS)

## Setup

### Option 1 — setup script (recommended)

```bash
bash setup.sh
```

This creates a `venv/`, upgrades pip, and installs all dependencies from `requirements.txt`.

### Option 2 — manual

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### Accessibility permission

The script posts synthetic mouse events, which requires **Accessibility** permission for your terminal app (Terminal, iTerm2, etc.).

On first run the script checks this automatically. If permission is missing it opens **System Settings → Privacy & Security → Accessibility** for you.

To grant it manually:
1. Open **System Settings → Privacy & Security → Accessibility**
2. Click **+** and add your terminal app
3. Enable the toggle next to it
4. Re-run the script

## Usage

```bash
# Default — nudge every 2 minutes
venv/bin/python3 stay_active.py

# Custom interval (seconds)
venv/bin/python3 stay_active.py --interval 60

# Help
venv/bin/python3 stay_active.py --help
```

Press `Ctrl+C` to stop. `caffeinate` is cleanly terminated and normal sleep behaviour is restored.

## Output

```
==================================================
  stay_active — system awake + staying active
==================================================
  Nudge interval : every 120s
  Press Ctrl+C to stop.
--------------------------------------------------
  Checking Accessibility permission... OK
  caffeinate PID : 12345
  [09:46:29] nudge #1 — idle 120.3s → 0.3s  [OK]
  [09:48:29] nudge #2 — idle 120.3s → 0.3s  [OK]
```

Each nudge line shows the idle time before and after:

| Status | Meaning |
|---|---|
| `[OK]` | Idle timer was reset successfully |
| `[FAILED]` | Timer did not reset — check Accessibility permission |

## Files

```
stay_active.py    # main script
requirements.txt  # Python dependencies
setup.sh          # one-shot setup script
venv/             # created by setup — not committed
```
