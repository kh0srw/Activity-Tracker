# Activity Tracker

A local-first activity and attention tracker rebuilt in Go for Linux + Hyprland.

The tracker has two independent parts:

- **Collector** — a tiny background service that listens to Hyprland IPC events and records focused-window spans, workspace changes, raw compositor events, and lightweight system samples.
- **Dashboard** — an on-demand local web UI. It is **not** kept running; start it only when you want to inspect your data.

No Telegram bot, no Streamlit, no Python runtime, no external database, and no cloud sync.

## What is tracked

Each focus span can include:

- start/end time and duration
- window class/application
- window title
- PID
- workspace id/name
- monitor id
- floating/fullscreen state
- XWayland/native Wayland state
- Hyprland raw events such as workspace/window/focus changes
- 1-minute load and memory samples

Data stays under `~/.local/share/activity-tracker/` by default. Runtime/control state stays under `~/.local/state/activity-tracker/`.

## Analytics

The dashboard/report engine computes metrics intended to describe attention quality, not just screen time:

- tracked time and elapsed workday span
- active density
- context switches and switches/hour
- short-focus fragmentation score
- focus score
- median and longest focus span
- 25+ minute same-app flow blocks and deep-work share
- bounce-back rate (`A → B → A` within two minutes)
- application entropy (how scattered usage is)
- per-workspace allocation
- hourly activity distribution
- daily breakdown and 7-day trend
- routine consistency
- top window contexts/titles
- local CSV export

These are behavioral heuristics, not medical or psychological measurements.

## Build on Ubuntu

```bash
git clone -b kh0srw https://github.com/kh0srw/Activity-Tracker.git
cd Activity-Tracker
go test ./...
go build -trimpath -ldflags="-s -w" -o activity-tracker ./cmd/activity-tracker
```

Go 1.23+ is recommended.

## Install the collector

```bash
./activity-tracker install
```

This copies the binary to `~/.local/bin/activity-tracker`, creates a user-level systemd service, and starts it.

Check it:

```bash
~/.local/bin/activity-tracker status
systemctl --user status activity-tracker.service
journalctl --user -u activity-tracker.service -f
```

The collector connects directly to Hyprland IPC. It can discover the current Hyprland runtime socket even when `HYPRLAND_INSTANCE_SIGNATURE` is not inherited by systemd.

## Open the dashboard only when needed

```bash
~/.local/bin/activity-tracker dashboard --days 7
```

It starts only on `127.0.0.1:8787` and opens your browser. Stop it with `Ctrl+C`.

Other examples:

```bash
activity-tracker dashboard --days 30
activity-tracker dashboard --days 14 --no-open
activity-tracker report --days 7
activity-tracker status
activity-tracker prune --keep-days 120
```

## Pause/resume tracking

```bash
activity-tracker pause
activity-tracker resume
activity-tracker toggle
```

Optional Hyprland bind for 0.55+ Lua config:

```lua
hl.bind("SUPER + SHIFT + P", hl.dsp.exec_cmd("~/.local/bin/activity-tracker toggle"))
```

For Hyprland 0.54 and older hyprlang configs:

```ini
bind = SUPER SHIFT, P, exec, ~/.local/bin/activity-tracker toggle
```

## Export

While the dashboard is running:

- open `http://127.0.0.1:8787/export.csv?days=7`
- or use the **Export CSV** button

Raw append-only files are also human-readable JSONL under:

```text
~/.local/share/activity-tracker/events/YYYY-MM-DD.jsonl
```

## Privacy

Window titles can contain document names, browser page titles, chats, or other sensitive context. This project stores them locally because they are useful for detailed analysis. Do not sync the data directory to a public location unless that is intentional.

The collector does **not** record keystrokes, clipboard contents, screenshots, or network traffic.

## Security note

The old Python implementation contained a Telegram bot token in repository history. The bot has been removed from the current codebase. A token that has ever been committed to a public repository must still be considered compromised and should be revoked/regenerated in BotFather; making the repository private later does not make the old token safe.
