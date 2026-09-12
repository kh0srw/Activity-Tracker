package model

import "time"

type Workspace struct {
	ID   int    `json:"id"`
	Name string `json:"name"`
}

type Window struct {
	Address      string    `json:"address"`
	Class        string    `json:"class"`
	Title        string    `json:"title"`
	InitialClass string    `json:"initial_class,omitempty"`
	InitialTitle string    `json:"initial_title,omitempty"`
	PID          int       `json:"pid"`
	Workspace    Workspace `json:"workspace"`
	Monitor      int       `json:"monitor"`
	Floating     bool      `json:"floating"`
	Fullscreen   bool      `json:"fullscreen"`
	XWayland     bool      `json:"xwayland"`
}

type Record struct {
	Kind       string         `json:"kind"`
	Timestamp  time.Time      `json:"timestamp,omitempty"`
	Start      time.Time      `json:"start,omitempty"`
	End        time.Time      `json:"end,omitempty"`
	DurationMS int64          `json:"duration_ms,omitempty"`
	Window     *Window        `json:"window,omitempty"`
	Event      string         `json:"event,omitempty"`
	Data       string         `json:"data,omitempty"`
	Load1      float64        `json:"load1,omitempty"`
	MemTotalKB int64          `json:"mem_total_kb,omitempty"`
	MemAvailKB int64          `json:"mem_available_kb,omitempty"`
	Meta       map[string]any `json:"meta,omitempty"`
}

type RuntimeState struct {
	PID       int       `json:"pid"`
	BootID    string    `json:"boot_id"`
	StartedAt time.Time `json:"started_at"`
	LastSeen  time.Time `json:"last_seen"`
	Paused    bool      `json:"paused"`
	SpanStart time.Time `json:"span_start,omitempty"`
	Window    *Window   `json:"window,omitempty"`
}
