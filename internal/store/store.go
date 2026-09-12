package store

import (
	"bufio"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/config"
	"github.com/kh0srw/Activity-Tracker/internal/model"
)

type Store struct {
	paths config.Paths
	mu    sync.Mutex
}

func New(paths config.Paths) *Store { return &Store{paths: paths} }

func (s *Store) Append(r model.Record) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	t := r.Timestamp
	if r.Kind == "span" {
		t = r.Start
	}
	if t.IsZero() {
		t = time.Now()
	}
	name := t.Local().Format("2006-01-02") + ".jsonl"
	path := filepath.Join(s.paths.EventsDir, name)
	f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o600)
	if err != nil {
		return err
	}
	defer f.Close()
	enc := json.NewEncoder(f)
	enc.SetEscapeHTML(false)
	return enc.Encode(r)
}

func (s *Store) LoadSpans(since time.Time) ([]model.Record, error) {
	files, err := os.ReadDir(s.paths.EventsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	cutoffDate := since.Local().Format("2006-01-02")
	var spans []model.Record
	for _, entry := range files {
		if entry.IsDir() || !strings.HasSuffix(entry.Name(), ".jsonl") {
			continue
		}
		day := strings.TrimSuffix(entry.Name(), ".jsonl")
		if day < cutoffDate {
			continue
		}
		if err := scanFile(filepath.Join(s.paths.EventsDir, entry.Name()), func(r model.Record) {
			if r.Kind == "span" && r.End.After(since) {
				spans = append(spans, r)
			}
		}); err != nil {
			return nil, err
		}
	}
	sort.Slice(spans, func(i, j int) bool { return spans[i].Start.Before(spans[j].Start) })
	return spans, nil
}

func (s *Store) LoadRecent(limit int) ([]model.Record, error) {
	if limit <= 0 {
		limit = 100
	}
	files, err := os.ReadDir(s.paths.EventsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}
	var names []string
	for _, e := range files {
		if !e.IsDir() && strings.HasSuffix(e.Name(), ".jsonl") {
			names = append(names, e.Name())
		}
	}
	sort.Sort(sort.Reverse(sort.StringSlice(names)))
	var out []model.Record
	for _, name := range names {
		var day []model.Record
		if err := scanFile(filepath.Join(s.paths.EventsDir, name), func(r model.Record) {
			if r.Kind == "span" {
				day = append(day, r)
			}
		}); err != nil {
			return nil, err
		}
		for i := len(day) - 1; i >= 0 && len(out) < limit; i-- {
			out = append(out, day[i])
		}
		if len(out) >= limit {
			break
		}
	}
	return out, nil
}

func scanFile(path string, fn func(model.Record)) error {
	f, err := os.Open(path)
	if err != nil {
		return err
	}
	defer f.Close()
	s := bufio.NewScanner(f)
	buf := make([]byte, 64*1024)
	s.Buffer(buf, 4*1024*1024)
	for s.Scan() {
		var r model.Record
		if json.Unmarshal(s.Bytes(), &r) == nil {
			fn(r)
		}
	}
	return s.Err()
}

func ExportCSV(w io.Writer, spans []model.Record) error {
	cw := csv.NewWriter(w)
	defer cw.Flush()
	if err := cw.Write([]string{"start", "end", "duration_seconds", "app", "title", "pid", "workspace_id", "workspace_name", "monitor", "floating", "fullscreen", "xwayland", "address"}); err != nil {
		return err
	}
	for _, r := range spans {
		if r.Window == nil {
			continue
		}
		win := r.Window
		row := []string{
			r.Start.Format(time.RFC3339Nano), r.End.Format(time.RFC3339Nano),
			fmt.Sprintf("%.3f", float64(r.DurationMS)/1000), win.Class, win.Title,
			strconv.Itoa(win.PID), strconv.Itoa(win.Workspace.ID), win.Workspace.Name,
			strconv.Itoa(win.Monitor), strconv.FormatBool(win.Floating), strconv.FormatBool(win.Fullscreen),
			strconv.FormatBool(win.XWayland), win.Address,
		}
		if err := cw.Write(row); err != nil {
			return err
		}
	}
	return cw.Error()
}

func Prune(paths config.Paths, keepDays int) (int, error) {
	if keepDays < 1 {
		return 0, fmt.Errorf("keep-days must be >= 1")
	}
	entries, err := os.ReadDir(paths.EventsDir)
	if err != nil {
		if os.IsNotExist(err) {
			return 0, nil
		}
		return 0, err
	}
	cutoff := time.Now().AddDate(0, 0, -keepDays).Local().Format("2006-01-02")
	removed := 0
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".jsonl") {
			continue
		}
		if strings.TrimSuffix(e.Name(), ".jsonl") < cutoff {
			if err := os.Remove(filepath.Join(paths.EventsDir, e.Name())); err != nil {
				return removed, err
			}
			removed++
		}
	}
	return removed, nil
}
