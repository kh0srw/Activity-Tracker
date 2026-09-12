package analysis

import (
	"testing"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/model"
)

func span(st time.Time, d time.Duration, app string) model.Record {
	return model.Record{Kind: "span", Start: st, End: st.Add(d), DurationMS: d.Milliseconds(), Window: &model.Window{Class: app, Workspace: model.Workspace{ID: 1, Name: "1"}}}
}

func TestAnalyzeSwitchAndDeepWork(t *testing.T) {
	base := time.Date(2026, 9, 12, 9, 0, 0, 0, time.Local)
	spans := []model.Record{span(base, 30*time.Minute, "code"), span(base.Add(30*time.Minute), time.Minute, "firefox"), span(base.Add(31*time.Minute), 35*time.Minute, "code")}
	s := Analyze(spans, base, base.Add(2*time.Hour))
	if s.ContextSwitches != 2 {
		t.Fatalf("switches=%d", s.ContextSwitches)
	}
	if s.FlowBlocks < 2 {
		t.Fatalf("flow blocks=%d", s.FlowBlocks)
	}
	if s.BounceRate <= 0 {
		t.Fatalf("expected bounce rate > 0")
	}
	if s.TrackedHours < 1.09 || s.TrackedHours > 1.11 {
		t.Fatalf("tracked=%f", s.TrackedHours)
	}
}

func TestNoData(t *testing.T) {
	s := Analyze(nil, time.Now().Add(-time.Hour), time.Now())
	if s.TrackedHours != 0 {
		t.Fatal("expected zero")
	}
}
