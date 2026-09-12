package systemstats

import (
	"bufio"
	"os"
	"strconv"
	"strings"

	"github.com/kh0srw/Activity-Tracker/internal/model"
)

func Sample() model.Record {
	r := model.Record{Kind: "sample"}
	if b, err := os.ReadFile("/proc/loadavg"); err == nil {
		f := strings.Fields(string(b))
		if len(f) > 0 {
			r.Load1, _ = strconv.ParseFloat(f[0], 64)
		}
	}
	if f, err := os.Open("/proc/meminfo"); err == nil {
		defer f.Close()
		s := bufio.NewScanner(f)
		for s.Scan() {
			p := strings.Fields(s.Text())
			if len(p) < 2 {
				continue
			}
			v, _ := strconv.ParseInt(p[1], 10, 64)
			switch strings.TrimSuffix(p[0], ":") {
			case "MemTotal":
				r.MemTotalKB = v
			case "MemAvailable":
				r.MemAvailKB = v
			}
		}
	}
	return r
}
