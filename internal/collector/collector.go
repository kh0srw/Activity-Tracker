package collector

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/config"
	"github.com/kh0srw/Activity-Tracker/internal/hypr"
	"github.com/kh0srw/Activity-Tracker/internal/model"
	"github.com/kh0srw/Activity-Tracker/internal/store"
	"github.com/kh0srw/Activity-Tracker/internal/systemstats"
)

type Collector struct {
	paths     config.Paths
	store     *store.Store
	minSpan   time.Duration
	current   *model.Window
	spanStart time.Time
	startedAt time.Time
	bootID    string
	paused    bool
}

func New(paths config.Paths) *Collector {
	return &Collector{paths: paths, store: store.New(paths), minSpan: 250 * time.Millisecond, startedAt: time.Now(), bootID: readBootID()}
}

func (c *Collector) Run(stop <-chan struct{}) error {
	if err := config.Ensure(c.paths); err != nil {
		return err
	}
	c.recoverLastState()
	c.paused = fileExists(c.paths.PauseFile)
	if !c.paused {
		c.refreshWindow(time.Now())
	}

	events := make(chan string, 128)
	errs := make(chan error, 8)
	go hypr.Listen(stop, events, errs)
	reconcile := time.NewTicker(10 * time.Second)
	defer reconcile.Stop()
	sample := time.NewTicker(60 * time.Second)
	defer sample.Stop()
	pauseCheck := time.NewTicker(time.Second)
	defer pauseCheck.Stop()
	midnightCheck := time.NewTicker(30 * time.Second)
	defer midnightCheck.Stop()

	log.Printf("collector started: data=%s", c.paths.DataDir)
	for {
		select {
		case <-stop:
			c.closeSpan(time.Now())
			c.writeRuntime(time.Now())
			return nil
		case line := <-events:
			name, data := hypr.ParseEvent(line)
			_ = c.store.Append(model.Record{Kind: "event", Timestamp: time.Now(), Event: name, Data: data})
			if !c.paused && hypr.ShouldRefresh(name) {
				c.refreshWindow(time.Now())
			}
		case err := <-errs:
			log.Printf("hyprland event socket: %v", err)
		case now := <-reconcile.C:
			if !c.paused {
				c.refreshWindow(now)
			}
			c.writeRuntime(now)
		case now := <-pauseCheck.C:
			c.syncPause(now)
		case now := <-sample.C:
			r := systemstats.Sample()
			r.Timestamp = now
			_ = c.store.Append(r)
		case now := <-midnightCheck.C:
			if c.current != nil && c.spanStart.Local().Format("2006-01-02") != now.Local().Format("2006-01-02") {
				c.closeSpan(now)
				c.spanStart = now
			}
		}
	}
}

func (c *Collector) syncPause(now time.Time) {
	p := fileExists(c.paths.PauseFile)
	if p == c.paused {
		return
	}
	c.paused = p
	if p {
		c.closeSpan(now)
		c.current = nil
		_ = c.store.Append(model.Record{Kind: "event", Timestamp: now, Event: "tracker_paused"})
	} else {
		_ = c.store.Append(model.Record{Kind: "event", Timestamp: now, Event: "tracker_resumed"})
		c.refreshWindow(now)
	}
	c.writeRuntime(now)
}

func (c *Collector) refreshWindow(now time.Time) {
	w, err := hypr.ActiveWindow()
	if err != nil {
		log.Printf("active window: %v", err)
		return
	}
	if sameWindow(c.current, w) {
		return
	}
	c.closeSpan(now)
	c.current = w
	if w != nil {
		c.spanStart = now
	}
	c.writeRuntime(now)
}

func sameWindow(a, b *model.Window) bool {
	if a == nil || b == nil {
		return a == b
	}
	return a.Address == b.Address && a.Class == b.Class && a.Title == b.Title && a.PID == b.PID &&
		a.Workspace.ID == b.Workspace.ID && a.Workspace.Name == b.Workspace.Name && a.Monitor == b.Monitor &&
		a.Floating == b.Floating && a.Fullscreen == b.Fullscreen
}

func (c *Collector) closeSpan(end time.Time) {
	if c.current == nil || c.spanStart.IsZero() || !end.After(c.spanStart) {
		return
	}
	d := end.Sub(c.spanStart)
	if d >= c.minSpan {
		w := *c.current
		_ = c.store.Append(model.Record{Kind: "span", Start: c.spanStart, End: end, DurationMS: d.Milliseconds(), Window: &w})
	}
	c.spanStart = time.Time{}
}

func (c *Collector) writeRuntime(now time.Time) {
	st := model.RuntimeState{PID: os.Getpid(), BootID: c.bootID, StartedAt: c.startedAt, LastSeen: now, Paused: c.paused, SpanStart: c.spanStart, Window: c.current}
	b, _ := json.MarshalIndent(st, "", "  ")
	tmp := c.paths.RuntimeFile + ".tmp"
	if os.WriteFile(tmp, b, 0o600) == nil {
		_ = os.Rename(tmp, c.paths.RuntimeFile)
	}
}

func (c *Collector) recoverLastState() {
	b, err := os.ReadFile(c.paths.RuntimeFile)
	if err != nil {
		return
	}
	var st model.RuntimeState
	if json.Unmarshal(b, &st) != nil {
		return
	}
	if st.BootID == "" || st.BootID != c.bootID || st.Window == nil || st.SpanStart.IsZero() || !st.LastSeen.After(st.SpanStart) {
		return
	}
	if time.Since(st.LastSeen) > 2*time.Minute {
		return
	}
	d := st.LastSeen.Sub(st.SpanStart)
	if d < c.minSpan {
		return
	}
	w := *st.Window
	_ = c.store.Append(model.Record{Kind: "span", Start: st.SpanStart, End: st.LastSeen, DurationMS: d.Milliseconds(), Window: &w, Meta: map[string]any{"recovered_after_restart": true}})
}

func readBootID() string {
	b, _ := os.ReadFile("/proc/sys/kernel/random/boot_id")
	return strings.TrimSpace(string(b))
}
func fileExists(path string) bool { _, err := os.Stat(path); return err == nil }

func SetPaused(paths config.Paths, paused bool) error {
	if err := config.Ensure(paths); err != nil {
		return err
	}
	if paused {
		return os.WriteFile(paths.PauseFile, []byte(time.Now().Format(time.RFC3339)), 0o600)
	}
	if err := os.Remove(paths.PauseFile); err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

func Toggle(paths config.Paths) (bool, error) {
	p := !fileExists(paths.PauseFile)
	return p, SetPaused(paths, p)
}

func ReadRuntime(paths config.Paths) (model.RuntimeState, error) {
	var st model.RuntimeState
	b, err := os.ReadFile(paths.RuntimeFile)
	if err != nil {
		return st, err
	}
	err = json.Unmarshal(b, &st)
	return st, err
}

func RuntimeSummary(paths config.Paths) string {
	st, err := ReadRuntime(paths)
	if err != nil {
		return fmt.Sprintf("collector: no runtime state (%v)", err)
	}
	alive := time.Since(st.LastSeen) < 30*time.Second
	app, title, ws := "-", "-", "-"
	if st.Window != nil {
		app, title, ws = st.Window.Class, st.Window.Title, st.Window.Workspace.Name
	}
	return fmt.Sprintf("collector_alive=%t paused=%t pid=%d last_seen=%s app=%q workspace=%q title=%q", alive, st.Paused, st.PID, st.LastSeen.Format(time.RFC3339), app, ws, title)
}

func InstalledBinaryPath() string {
	home, _ := os.UserHomeDir()
	return filepath.Join(home, ".local", "bin", "activity-tracker")
}
