package analysis

import (
	"math"
	"sort"
	"strings"
	"time"

	"github.com/kh0srw/Activity-Tracker/internal/model"
)

type Bucket struct {
	Name    string  `json:"name"`
	Seconds float64 `json:"seconds"`
	Percent float64 `json:"percent"`
}
type Day struct {
	Date      string  `json:"date"`
	Hours     float64 `json:"hours"`
	Switches  int     `json:"switches"`
	DeepHours float64 `json:"deep_hours"`
	First     string  `json:"first"`
	Last      string  `json:"last"`
}
type Hour struct {
	Hour     int     `json:"hour"`
	Seconds  float64 `json:"seconds"`
	Switches int     `json:"switches"`
}
type Insight struct {
	Level string `json:"level"`
	Title string `json:"title"`
	Text  string `json:"text"`
}

type Summary struct {
	From                time.Time `json:"from"`
	To                  time.Time `json:"to"`
	TrackedHours        float64   `json:"tracked_hours"`
	WorkdaySpanHours    float64   `json:"workday_span_hours"`
	ActiveDensity       float64   `json:"active_density"`
	FocusScore          float64   `json:"focus_score"`
	FragmentationScore  float64   `json:"fragmentation_score"`
	ContextSwitches     int       `json:"context_switches"`
	SwitchesPerHour     float64   `json:"switches_per_hour"`
	BounceRate          float64   `json:"bounce_rate"`
	MedianFocusMinutes  float64   `json:"median_focus_minutes"`
	LongestFocusMinutes float64   `json:"longest_focus_minutes"`
	DeepWorkHours       float64   `json:"deep_work_hours"`
	DeepWorkRatio       float64   `json:"deep_work_ratio"`
	FlowBlocks          int       `json:"flow_blocks"`
	AppEntropy          float64   `json:"app_entropy"`
	UniqueApps          int       `json:"unique_apps"`
	SessionCount        int       `json:"session_count"`
	LongestSessionHours float64   `json:"longest_session_hours"`
	PeakHour            int       `json:"peak_hour"`
	SevenDayTrendPct    float64   `json:"seven_day_trend_pct"`
	RoutineConsistency  float64   `json:"routine_consistency"`
	Apps                []Bucket  `json:"apps"`
	Workspaces          []Bucket  `json:"workspaces"`
	Contexts            []Bucket  `json:"contexts"`
	Days                []Day     `json:"days"`
	Hours               []Hour    `json:"hours"`
	Insights            []Insight `json:"insights"`
}

type run struct {
	start, end time.Time
	app        string
	workspace  string
	seconds    float64
}

func Analyze(spans []model.Record, since time.Time, now time.Time) Summary {
	s := Summary{From: since, To: now, PeakHour: -1}
	if len(spans) == 0 {
		return s
	}
	sort.Slice(spans, func(i, j int) bool { return spans[i].Start.Before(spans[j].Start) })

	appSec, wsSec, ctxSec := map[string]float64{}, map[string]float64{}, map[string]float64{}
	durList := []float64{}
	hourSec := make([]float64, 24)
	hourSwitch := make([]int, 24)
	type dayAgg struct {
		sec, deep  float64
		switches   int
		first, last time.Time
	}
	days := map[string]*dayAgg{}
	var total float64
	var first, last time.Time
	prevApp := ""
	prevEnd := time.Time{}
	short := 0
	switches := 0

	for _, r := range spans {
		if r.Window == nil || !r.End.After(r.Start) {
			continue
		}
		st := maxTime(r.Start, since)
		en := minTime(r.End, now)
		if !en.After(st) {
			continue
		}
		sec := en.Sub(st).Seconds()
		total += sec
		durList = append(durList, sec)
		app := clean(r.Window.Class)
		if app == "" {
			app = "unknown"
		}
		appSec[app] += sec
		ws := r.Window.Workspace.Name
		if ws == "" {
			ws = "workspace-" + itoa(r.Window.Workspace.ID)
		}
		wsSec[ws] += sec
		ctx := strings.TrimSpace(r.Window.Title)
		if ctx != "" {
			ctxSec[app+" · "+ctx] += sec
		}
		if sec < 120 {
			short++
		}
		if first.IsZero() || st.Before(first) {
			first = st
		}
		if last.IsZero() || en.After(last) {
			last = en
		}
		dayKey := st.Local().Format("2006-01-02")
		da := days[dayKey]
		if da == nil {
			da = &dayAgg{}
			days[dayKey] = da
		}
		da.sec += sec
		if da.first.IsZero() || st.Before(da.first) {
			da.first = st
		}
		if da.last.IsZero() || en.After(da.last) {
			da.last = en
		}
		if prevApp != "" && app != prevApp && st.Sub(prevEnd) <= 15*time.Minute {
			switches++
			da.switches++
			hourSwitch[st.Local().Hour()]++
		}
		prevApp, prevEnd = app, en
		allocateHours(hourSec, st, en)
	}
	if total <= 0 {
		return s
	}
	s.TrackedHours = total / 3600
	s.UniqueApps = len(appSec)
	s.ContextSwitches = switches
	s.SwitchesPerHour = float64(switches) / s.TrackedHours
	s.WorkdaySpanHours = last.Sub(first).Hours()
	if s.WorkdaySpanHours > 0 {
		s.ActiveDensity = clamp(total/(s.WorkdaySpanHours*3600)*100, 0, 100)
	}
	s.MedianFocusMinutes = median(durList) / 60

	runs := mergeRuns(spans, since, now)
	for _, r := range runs {
		mins := r.seconds / 60
		if mins > s.LongestFocusMinutes {
			s.LongestFocusMinutes = mins
		}
		if mins >= 25 {
			s.DeepWorkHours += r.seconds / 3600
			s.FlowBlocks++
			if da := days[r.start.Local().Format("2006-01-02")]; da != nil {
				da.deep += r.seconds
			}
		}
	}
	s.DeepWorkRatio = clamp(s.DeepWorkHours/s.TrackedHours*100, 0, 100)
	s.BounceRate = bounceRate(spans, since, now)
	s.AppEntropy = entropy(appSec)
	shortRatio := float64(short) / float64(maxInt(1, len(durList)))
	s.FragmentationScore = clamp(100*(0.45*shortRatio+0.35*math.Min(s.SwitchesPerHour/20, 1)+0.20*s.AppEntropy), 0, 100)
	s.FocusScore = clamp(100-0.75*s.FragmentationScore+0.25*s.DeepWorkRatio, 0, 100)
	s.SessionCount, s.LongestSessionHours = sessions(spans, since, now)
	s.Apps = buckets(appSec, total, 12)
	s.Workspaces = buckets(wsSec, total, 12)
	s.Contexts = buckets(ctxSec, total, 12)
	for h := 0; h < 24; h++ {
		s.Hours = append(s.Hours, Hour{Hour: h, Seconds: hourSec[h], Switches: hourSwitch[h]})
		if s.PeakHour < 0 || hourSec[h] > hourSec[s.PeakHour] {
			s.PeakHour = h
		}
	}

	var dayKeys []string
	for k := range days {
		dayKeys = append(dayKeys, k)
	}
	sort.Strings(dayKeys)
	var dailyHours []float64
	var startMinutes []float64
	for _, k := range dayKeys {
		d := days[k]
		hrs := d.sec / 3600
		dailyHours = append(dailyHours, hrs)
		startMinutes = append(startMinutes, float64(d.first.Hour()*60+d.first.Minute()))
		s.Days = append(s.Days, Day{Date: k, Hours: hrs, Switches: d.switches, DeepHours: d.deep / 3600, First: d.first.Format("15:04"), Last: d.last.Format("15:04")})
	}
	s.SevenDayTrendPct = trendPct(lastN(dailyHours, 7))
	s.RoutineConsistency = routineConsistency(startMinutes)
	s.Insights = buildInsights(s)
	return s
}

func mergeRuns(spans []model.Record, since, now time.Time) []run {
	var out []run
	for _, x := range spans {
		if x.Window == nil {
			continue
		}
		st := maxTime(x.Start, since)
		en := minTime(x.End, now)
		if !en.After(st) {
			continue
		}
		app := clean(x.Window.Class)
		ws := x.Window.Workspace.Name
		sec := en.Sub(st).Seconds()
		if len(out) > 0 {
			last := &out[len(out)-1]
			if last.app == app && last.workspace == ws && st.Sub(last.end) <= 15*time.Second {
				last.end = en
				last.seconds += sec + math.Max(0, st.Sub(last.end).Seconds())
				continue
			}
		}
		out = append(out, run{start: st, end: en, app: app, workspace: ws, seconds: sec})
	}
	for i := range out {
		out[i].seconds = out[i].end.Sub(out[i].start).Seconds()
	}
	return out
}

func bounceRate(spans []model.Record, since, now time.Time) float64 {
	type x struct {
		app    string
		st, en time.Time
	}
	var a []x
	for _, r := range spans {
		if r.Window == nil {
			continue
		}
		st := maxTime(r.Start, since)
		en := minTime(r.End, now)
		if en.After(st) {
			a = append(a, x{clean(r.Window.Class), st, en})
		}
	}
	bounces, opportunities := 0, 0
	for i := 0; i+2 < len(a); i++ {
		if a[i].app == "" || a[i+1].app == "" || a[i].app == a[i+1].app {
			continue
		}
		opportunities++
		if a[i].app == a[i+2].app && a[i+1].en.Sub(a[i+1].st) <= 2*time.Minute && a[i+1].st.Sub(a[i].en) <= 30*time.Second && a[i+2].st.Sub(a[i+1].en) <= 30*time.Second {
			bounces++
		}
	}
	if opportunities == 0 {
		return 0
	}
	return float64(bounces) / float64(opportunities) * 100
}

func sessions(spans []model.Record, since, now time.Time) (int, float64) {
	count := 0
	longest := 0.0
	var ss, se time.Time
	for _, r := range spans {
		if r.Window == nil {
			continue
		}
		st := maxTime(r.Start, since)
		en := minTime(r.End, now)
		if !en.After(st) {
			continue
		}
		if ss.IsZero() || st.Sub(se) > 15*time.Minute {
			if !ss.IsZero() {
				longest = math.Max(longest, se.Sub(ss).Hours())
			}
			count++
			ss = st
		}
		se = en
	}
	if !ss.IsZero() {
		longest = math.Max(longest, se.Sub(ss).Hours())
	}
	return count, longest
}

func allocateHours(dst []float64, st, en time.Time) {
	for cur := st; cur.Before(en); {
		next := time.Date(cur.Year(), cur.Month(), cur.Day(), cur.Hour()+1, 0, 0, 0, cur.Location())
		if next.After(en) {
			next = en
		}
		dst[cur.Hour()] += next.Sub(cur).Seconds()
		cur = next
	}
}
func buckets(m map[string]float64, total float64, n int) []Bucket {
	type kv struct {
		k string
		v float64
	}
	a := make([]kv, 0, len(m))
	for k, v := range m {
		a = append(a, kv{k, v})
	}
	sort.Slice(a, func(i, j int) bool { return a[i].v > a[j].v })
	if len(a) > n {
		a = a[:n]
	}
	out := make([]Bucket, 0, len(a))
	for _, x := range a {
		out = append(out, Bucket{Name: x.k, Seconds: x.v, Percent: x.v / total * 100})
	}
	return out
}
func entropy(m map[string]float64) float64 {
	if len(m) <= 1 {
		return 0
	}
	var total float64
	for _, v := range m {
		total += v
	}
	var e float64
	for _, v := range m {
		p := v / total
		if p > 0 {
			e -= p * math.Log(p)
		}
	}
	return e / math.Log(float64(len(m)))
}
func median(a []float64) float64 {
	if len(a) == 0 {
		return 0
	}
	b := append([]float64(nil), a...)
	sort.Float64s(b)
	m := len(b) / 2
	if len(b)%2 == 1 {
		return b[m]
	}
	return (b[m-1] + b[m]) / 2
}
func trendPct(v []float64) float64 {
	if len(v) < 2 {
		return 0
	}
	n := float64(len(v))
	var sx, sy, sxy, sxx float64
	for i, y := range v {
		x := float64(i)
		sx += x
		sy += y
		sxy += x * y
		sxx += x * x
	}
	den := n*sxx - sx*sx
	if den == 0 {
		return 0
	}
	slope := (n*sxy - sx*sy) / den
	avg := sy / n
	if avg == 0 {
		return 0
	}
	return slope / avg * 100
}
func routineConsistency(v []float64) float64 {
	if len(v) < 2 {
		return 100
	}
	var sum float64
	for _, x := range v {
		sum += x
	}
	avg := sum / float64(len(v))
	var q float64
	for _, x := range v {
		d := x - avg
		q += d * d
	}
	std := math.Sqrt(q / float64(len(v)))
	return clamp(100-std/180*100, 0, 100)
}
func buildInsights(s Summary) []Insight {
	var o []Insight
	if s.SwitchesPerHour >= 15 {
		o = append(o, Insight{"warning", "High context switching", "You switch applications very frequently. Batch chat/browser checks and protect longer single-app blocks."})
	} else if s.SwitchesPerHour <= 6 && s.TrackedHours >= 2 {
		o = append(o, Insight{"good", "Low context switching", "Your application switching rate is low for the tracked period."})
	}
	if s.BounceRate >= 25 {
		o = append(o, Insight{"warning", "Frequent bounce-backs", "Many switches return to the previous app within two minutes, a strong sign of interruption-driven work."})
	}
	if s.DeepWorkRatio >= 45 {
		o = append(o, Insight{"good", "Strong deep-work share", "A large share of tracked time is in 25+ minute same-app focus blocks."})
	} else if s.TrackedHours >= 3 && s.DeepWorkRatio < 20 {
		o = append(o, Insight{"info", "Few long focus blocks", "Less than one fifth of tracked time forms 25+ minute same-app blocks."})
	}
	if s.ActiveDensity < 55 && s.WorkdaySpanHours >= 4 {
		o = append(o, Insight{"info", "Workday is spread out", "Tracked work is distributed across a long elapsed window. Check whether long gaps are intentional."})
	}
	if math.Abs(s.SevenDayTrendPct) >= 8 {
		dir := "up"
		if s.SevenDayTrendPct < 0 {
			dir = "down"
		}
		o = append(o, Insight{"info", "7-day activity trend", "Daily tracked time is trending " + dir + " relative to the recent baseline."})
	}
	return o
}
func clean(s string) string {
	s = strings.TrimSpace(strings.ToLower(s))
	if strings.HasSuffix(s, ".exe") {
		s = strings.TrimSuffix(s, ".exe")
	}
	return s
}
func clamp(x, a, b float64) float64 {
	if x < a {
		return a
	}
	if x > b {
		return b
	}
	return x
}
func maxTime(a, b time.Time) time.Time {
	if a.After(b) {
		return a
	}
	return b
}
func minTime(a, b time.Time) time.Time {
	if a.Before(b) {
		return a
	}
	return b
}
func lastN(v []float64, n int) []float64 {
	if len(v) <= n {
		return v
	}
	return v[len(v)-n:]
}
func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}
func itoa(n int) string {
	if n == 0 {
		return "0"
	}
	neg := n < 0
	if neg {
		n = -n
	}
	b := make([]byte, 0, 12)
	for n > 0 {
		b = append([]byte{byte('0' + n%10)}, b...)
		n /= 10
	}
	if neg {
		b = append([]byte{'-'}, b...)
	}
	return string(b)
}
