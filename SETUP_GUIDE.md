# Ubuntu + Hyprland setup

## 1. Requirements

Verify Hyprland and Go:

```bash
hyprctl version
go version
```

If Go is missing, install a current Go release (1.23+ recommended) from Ubuntu packages or the official Go distribution.

## 2. Build

```bash
git clone -b kh0srw https://github.com/kh0srw/Activity-Tracker.git
cd Activity-Tracker
go test ./...
go build -trimpath -ldflags="-s -w" -o activity-tracker ./cmd/activity-tracker
```

## 3. Test without installing

Run the collector in a terminal:

```bash
./activity-tracker collect
```

Switch between a few windows/workspaces for a minute, then stop with `Ctrl+C`.

Inspect the data:

```bash
./activity-tracker report --days 1
./activity-tracker dashboard --days 1
```

## 4. Install persistent collector

```bash
./activity-tracker install
```

The collector now starts as a **user** systemd service. The dashboard does not.

Useful commands:

```bash
systemctl --user status activity-tracker.service
systemctl --user restart activity-tracker.service
journalctl --user -u activity-tracker.service -n 100 --no-pager
activity-tracker status
```

## 5. Dashboard on demand

```bash
activity-tracker dashboard --days 7
```

Default URL:

```text
http://127.0.0.1:8787
```

Stop the dashboard with `Ctrl+C`. Collection continues in the background.

## 6. Pause/resume

```bash
activity-tracker toggle
```

Hyprland 0.55+ (`hyprland.lua`):

```lua
hl.bind("SUPER + SHIFT + P", hl.dsp.exec_cmd("~/.local/bin/activity-tracker toggle"))
```

Hyprland <=0.54 (`hyprland.conf`):

```ini
bind = SUPER SHIFT, P, exec, ~/.local/bin/activity-tracker toggle
```

## 7. Data locations

```text
~/.local/share/activity-tracker/events/   raw daily JSONL
~/.local/state/activity-tracker/runtime.json
~/.local/state/activity-tracker/paused    present only while paused
```

Override XDG locations with `XDG_DATA_HOME` and `XDG_STATE_HOME`.

## 8. Remove service

```bash
activity-tracker uninstall
```

This removes the service but intentionally keeps collected data.

To delete data too:

```bash
rm -rf ~/.local/share/activity-tracker ~/.local/state/activity-tracker
```
