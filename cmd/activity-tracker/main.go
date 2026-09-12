package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"syscall"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/analysis"
	"github.com/kh0srw/Activity-Tracker/internal/collector"
	"github.com/kh0srw/Activity-Tracker/internal/config"
	"github.com/kh0srw/Activity-Tracker/internal/dashboard"
	"github.com/kh0srw/Activity-Tracker/internal/store"
)

const version = "2.0.0"

func main() {
	log.SetFlags(log.LstdFlags | log.Lmicroseconds)
	if len(os.Args) < 2 {
		usage()
		os.Exit(2)
	}
	paths := config.DefaultPaths()
	var err error
	switch os.Args[1] {
	case "collect":
		err = runCollect(paths, os.Args[2:])
	case "dashboard":
		err = runDashboard(paths, os.Args[2:])
	case "report":
		err = runReport(paths, os.Args[2:])
	case "pause":
		err = collector.SetPaused(paths, true)
		if err == nil {
			fmt.Println("tracking paused")
		}
	case "resume":
		err = collector.SetPaused(paths, false)
		if err == nil {
			fmt.Println("tracking resumed")
		}
	case "toggle":
		var paused bool
		paused, err = collector.Toggle(paths)
		if err == nil {
			if paused {
				fmt.Println("tracking paused")
			} else {
				fmt.Println("tracking resumed")
			}
		}
	case "status":
		fmt.Println(collector.RuntimeSummary(paths))
	case "install":
		err = install(paths)
	case "uninstall":
		err = uninstall()
	case "prune":
		err = runPrune(paths, os.Args[2:])
	case "version", "--version", "-v":
		fmt.Println(version)
	case "help", "--help", "-h":
		usage()
	default:
		usage()
		os.Exit(2)
	}
	if err != nil {
		log.Fatal(err)
	}
}

func usage() {
	fmt.Print(`Activity Tracker v` + version + `

Usage:
  activity-tracker collect                 run the Hyprland collector
  activity-tracker dashboard [--days 7]   start the local dashboard on demand
  activity-tracker report [--days 7]      print JSON analytics
  activity-tracker pause|resume|toggle     control collection without stopping service
  activity-tracker status                  show live collector state
  activity-tracker install                 install binary + user systemd service
  activity-tracker uninstall               remove user systemd service
  activity-tracker prune --keep-days 90    delete old daily event files
  activity-tracker version
`)
}

func runCollect(paths config.Paths, args []string) error {
	fs := flag.NewFlagSet("collect", flag.ContinueOnError)
	data := fs.String("data-dir", "", "override data directory")
	state := fs.String("state-dir", "", "override state directory")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *data != "" || *state != "" {
		d := paths.DataDir
		s := paths.StateDir
		if *data != "" {
			d = *data
		}
		if *state != "" {
			s = *state
		}
		paths = config.FromDirs(d, s)
	}
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	return collector.New(paths).Run(ctx.Done())
}

func runDashboard(paths config.Paths, args []string) error {
	fs := flag.NewFlagSet("dashboard", flag.ContinueOnError)
	days := fs.Int("days", 7, "days to load")
	addr := fs.String("addr", "127.0.0.1:8787", "listen address")
	noOpen := fs.Bool("no-open", false, "do not open browser")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if *days < 1 || *days > 365 {
		return fmt.Errorf("days must be 1..365")
	}
	s, err := dashboard.New(paths, *addr, *days, !*noOpen)
	if err != nil {
		return err
	}
	return s.Run()
}

func runReport(paths config.Paths, args []string) error {
	fs := flag.NewFlagSet("report", flag.ContinueOnError)
	days := fs.Int("days", 7, "days to analyze")
	if err := fs.Parse(args); err != nil {
		return err
	}
	since := time.Now().AddDate(0, 0, -*days)
	spans, err := store.New(paths).LoadSpans(since)
	if err != nil {
		return err
	}
	s := analysis.Analyze(spans, since, time.Now())
	b, _ := json.MarshalIndent(s, "", "  ")
	fmt.Println(string(b))
	return nil
}

func runPrune(paths config.Paths, args []string) error {
	fs := flag.NewFlagSet("prune", flag.ContinueOnError)
	keep := fs.Int("keep-days", 90, "days to keep")
	if err := fs.Parse(args); err != nil {
		return err
	}
	n, err := store.Prune(paths, *keep)
	if err == nil {
		fmt.Printf("removed %d daily files\n", n)
	}
	return err
}

func install(paths config.Paths) error {
	if err := config.Ensure(paths); err != nil {
		return err
	}
	src, err := os.Executable()
	if err != nil {
		return err
	}
	dst := collector.InstalledBinaryPath()
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	if err := copyFile(src, dst, 0o755); err != nil {
		return err
	}
	home, _ := os.UserHomeDir()
	unitDir := filepath.Join(home, ".config", "systemd", "user")
	if err := os.MkdirAll(unitDir, 0o755); err != nil {
		return err
	}
	unit := `[Unit]
Description=Activity Tracker for Hyprland
After=graphical-session.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=` + dst + ` collect
Restart=on-failure
RestartSec=3
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
`
	unitPath := filepath.Join(unitDir, "activity-tracker.service")
	if err := os.WriteFile(unitPath, []byte(unit), 0o644); err != nil {
		return err
	}
	if err := run("systemctl", "--user", "daemon-reload"); err != nil {
		return err
	}
	if err := run("systemctl", "--user", "enable", "--now", "activity-tracker.service"); err != nil {
		return err
	}
	fmt.Printf("installed %s\ncollector service enabled\n", dst)
	return nil
}

func uninstall() error {
	_ = run("systemctl", "--user", "disable", "--now", "activity-tracker.service")
	home, _ := os.UserHomeDir()
	_ = os.Remove(filepath.Join(home, ".config", "systemd", "user", "activity-tracker.service"))
	_ = run("systemctl", "--user", "daemon-reload")
	fmt.Println("service removed; activity data was kept")
	return nil
}
func run(name string, args ...string) error {
	c := exec.Command(name, args...)
	c.Stdout = os.Stdout
	c.Stderr = os.Stderr
	return c.Run()
}
func copyFile(src, dst string, mode os.FileMode) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.OpenFile(dst, os.O_CREATE|os.O_TRUNC|os.O_WRONLY, mode)
	if err != nil {
		return err
	}
	if _, err = io.Copy(out, in); err != nil {
		out.Close()
		return err
	}
	return out.Close()
}
