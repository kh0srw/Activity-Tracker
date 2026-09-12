package hypr

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/model"
)

type activeWindowJSON struct {
	Address      string          `json:"address"`
	Mapped       bool            `json:"mapped"`
	Class        string          `json:"class"`
	Title        string          `json:"title"`
	InitialClass string          `json:"initialClass"`
	InitialTitle string          `json:"initialTitle"`
	PID          int             `json:"pid"`
	Workspace    model.Workspace `json:"workspace"`
	Monitor      int             `json:"monitor"`
	Floating     bool            `json:"floating"`
	Fullscreen   any             `json:"fullscreen"`
	XWayland     bool            `json:"xwayland"`
}

func socketPaths() (string, string, error) {
	runtimeDir := os.Getenv("XDG_RUNTIME_DIR")
	if runtimeDir == "" {
		runtimeDir = fmt.Sprintf("/run/user/%d", os.Getuid())
	}
	if sig := os.Getenv("HYPRLAND_INSTANCE_SIGNATURE"); sig != "" {
		base := filepath.Join(runtimeDir, "hypr", sig)
		if fileExists(filepath.Join(base, ".socket.sock")) && fileExists(filepath.Join(base, ".socket2.sock")) {
			return filepath.Join(base, ".socket.sock"), filepath.Join(base, ".socket2.sock"), nil
		}
	}
	matches, _ := filepath.Glob(filepath.Join(runtimeDir, "hypr", "*", ".socket2.sock"))
	if len(matches) == 0 {
		return "", "", errors.New("no Hyprland IPC socket found; is Hyprland running?")
	}
	best := matches[0]
	var bestTime time.Time
	for _, m := range matches {
		if st, err := os.Stat(m); err == nil && st.ModTime().After(bestTime) {
			best, bestTime = m, st.ModTime()
		}
	}
	base := filepath.Dir(best)
	cmd := filepath.Join(base, ".socket.sock")
	if !fileExists(cmd) {
		return "", "", errors.New("Hyprland command socket missing")
	}
	return cmd, best, nil
}

func fileExists(path string) bool { _, err := os.Stat(path); return err == nil }

func ActiveWindow() (*model.Window, error) {
	cmdSock, _, err := socketPaths()
	if err != nil {
		return nil, err
	}
	c, err := net.DialTimeout("unix", cmdSock, 1200*time.Millisecond)
	if err != nil {
		return nil, err
	}
	defer c.Close()
	_ = c.SetDeadline(time.Now().Add(1500 * time.Millisecond))
	if _, err := io.WriteString(c, "j/activewindow"); err != nil {
		return nil, err
	}
	b, err := io.ReadAll(c)
	if err != nil {
		return nil, err
	}
	if len(strings.TrimSpace(string(b))) == 0 || strings.TrimSpace(string(b)) == "{}" {
		return nil, nil
	}
	var aw activeWindowJSON
	if err := json.Unmarshal(b, &aw); err != nil {
		return nil, fmt.Errorf("decode activewindow: %w", err)
	}
	if !aw.Mapped && aw.Address == "" && aw.Class == "" {
		return nil, nil
	}
	return &model.Window{
		Address: aw.Address, Class: aw.Class, Title: truncate(aw.Title, 2048),
		InitialClass: aw.InitialClass, InitialTitle: truncate(aw.InitialTitle, 2048),
		PID: aw.PID, Workspace: aw.Workspace, Monitor: aw.Monitor, Floating: aw.Floating,
		Fullscreen: parseBoolish(aw.Fullscreen), XWayland: aw.XWayland,
	}, nil
}

func parseBoolish(v any) bool {
	switch x := v.(type) {
	case bool:
		return x
	case float64:
		return x != 0
	case string:
		b, _ := strconv.ParseBool(x)
		if b {
			return true
		}
		i, _ := strconv.Atoi(x)
		return i != 0
	default:
		return false
	}
}

func Listen(stop <-chan struct{}, out chan<- string, errs chan<- error) {
	for {
		select {
		case <-stop:
			return
		default:
		}
		_, eventSock, err := socketPaths()
		if err != nil {
			errs <- err
			if !sleepOrStop(stop, 2*time.Second) {
				return
			}
			continue
		}
		c, err := net.DialTimeout("unix", eventSock, 1500*time.Millisecond)
		if err != nil {
			errs <- err
			if !sleepOrStop(stop, 2*time.Second) {
				return
			}
			continue
		}
		s := bufio.NewScanner(c)
		for s.Scan() {
			select {
			case out <- s.Text():
			case <-stop:
				_ = c.Close()
				return
			}
		}
		if err := s.Err(); err != nil {
			errs <- err
		}
		_ = c.Close()
		if !sleepOrStop(stop, time.Second) {
			return
		}
	}
}

func ParseEvent(line string) (name, data string) {
	parts := strings.SplitN(line, ">>", 2)
	if len(parts) == 1 {
		return parts[0], ""
	}
	return parts[0], parts[1]
}

func ShouldRefresh(name string) bool {
	switch name {
	case "activewindow", "activewindowv2", "workspace", "workspacev2", "focusedmon", "focusedmonv2", "openwindow", "closewindow", "movewindow", "movewindowv2", "fullscreen", "changefloatingmode", "windowtitle", "minimized":
		return true
	default:
		return false
	}
}

func sleepOrStop(stop <-chan struct{}, d time.Duration) bool {
	t := time.NewTimer(d)
	defer t.Stop()
	select {
	case <-t.C:
		return true
	case <-stop:
		return false
	}
}

func truncate(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}
