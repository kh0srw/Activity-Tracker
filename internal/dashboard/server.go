package dashboard

import (
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"os/exec"
	"strconv"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/analysis"
	"github.com/kh0srw/Activity-Tracker/internal/config"
	"github.com/kh0srw/Activity-Tracker/internal/store"
)

type Server struct {
	paths       config.Paths
	addr        string
	defaultDays int
	open        bool
	tmpl        *template.Template
}

func New(paths config.Paths, addr string, days int, open bool) (*Server, error) {
	funcs := template.FuncMap{"hours": func(sec float64) string { return fmt.Sprintf("%.1fh", sec/3600) }, "dur": func(sec float64) string {
		if sec < 3600 {
			return fmt.Sprintf("%.0fm", sec/60)
		}
		return fmt.Sprintf("%.1fh", sec/3600)
	}, "pct": func(v float64) string { return fmt.Sprintf("%.0f%%", v) }, "f1": func(v float64) string { return fmt.Sprintf("%.1f", v) }, "hour": func(h int) string {
		if h < 0 {
			return "-"
		}
		return fmt.Sprintf("%02d:00", h)
	}, "hourHeight": func(sec float64, hours []analysis.Hour) float64 {
		max := 0.0
		for _, x := range hours {
			if x.Seconds > max {
				max = x.Seconds
			}
		}
		if max <= 0 {
			return 2
		}
		v := sec / max * 100
		if v < 2 {
			return 2
		}
		return v
	}, "msdur": func(ms int64) string {
		sec := float64(ms) / 1000
		if sec < 60 {
			return fmt.Sprintf("%.0fs", sec)
		}
		if sec < 3600 {
			return fmt.Sprintf("%.1fm", sec/60)
		}
		return fmt.Sprintf("%.1fh", sec/3600)
	}}
	t, err := template.New("dashboard").Funcs(funcs).Parse(pageTemplate)
	if err != nil {
		return nil, err
	}
	return &Server{paths: paths, addr: addr, defaultDays: days, open: open, tmpl: t}, nil
}

func (s *Server) Run() error {
	mux := http.NewServeMux()
	mux.HandleFunc("/", s.handleHome)
	mux.HandleFunc("/api/summary", s.handleSummary)
	mux.HandleFunc("/export.csv", s.handleCSV)
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("ok")) })
	url := "http://" + s.addr
	log.Printf("dashboard: %s", url)
	if s.open {
		go func() {
			time.Sleep(300 * time.Millisecond)
			_ = exec.Command("xdg-open", url).Start()
		}()
	}
	return http.ListenAndServe(s.addr, mux)
}

func (s *Server) days(r *http.Request) int {
	d := s.defaultDays
	if x, err := strconv.Atoi(r.URL.Query().Get("days")); err == nil && x >= 1 && x <= 365 {
		d = x
	}
	return d
}
func (s *Server) load(days int) (analysis.Summary, []any, error) {
	st := store.New(s.paths)
	since := time.Now().AddDate(0, 0, -days)
	spans, err := st.LoadSpans(since)
	if err != nil {
		return analysis.Summary{}, nil, err
	}
	sum := analysis.Analyze(spans, since, time.Now())
	recent, _ := st.LoadRecent(120)
	items := make([]any, 0, len(recent))
	for _, r := range recent {
		items = append(items, r)
	}
	return sum, items, nil
}

func (s *Server) handleHome(w http.ResponseWriter, r *http.Request) {
	d := s.days(r)
	sum, recent, err := s.load(d)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	data := struct {
		Days    int
		Summary analysis.Summary
		Recent  []any
	}{d, sum, recent}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := s.tmpl.Execute(w, data); err != nil {
		log.Printf("template: %v", err)
	}
}
func (s *Server) handleSummary(w http.ResponseWriter, r *http.Request) {
	d := s.days(r)
	sum, _, err := s.load(d)
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(sum)
}
func (s *Server) handleCSV(w http.ResponseWriter, r *http.Request) {
	d := s.days(r)
	st := store.New(s.paths)
	spans, err := st.LoadSpans(time.Now().AddDate(0, 0, -d))
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	w.Header().Set("Content-Type", "text/csv")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=activity-%dd.csv", d))
	_ = store.ExportCSV(w, spans)
}
