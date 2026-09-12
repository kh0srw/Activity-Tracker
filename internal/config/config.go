package config

import (
	"os"
	"path/filepath"
)

type Paths struct {
	DataDir     string
	EventsDir   string
	StateDir    string
	PauseFile   string
	RuntimeFile string
}

func DefaultPaths() Paths {
	home, _ := os.UserHomeDir()
	dataBase := os.Getenv("XDG_DATA_HOME")
	if dataBase == "" {
		dataBase = filepath.Join(home, ".local", "share")
	}
	stateBase := os.Getenv("XDG_STATE_HOME")
	if stateBase == "" {
		stateBase = filepath.Join(home, ".local", "state")
	}
	return FromDirs(filepath.Join(dataBase, "activity-tracker"), filepath.Join(stateBase, "activity-tracker"))
}

func FromDirs(dataDir, stateDir string) Paths {
	return Paths{
		DataDir:     dataDir,
		EventsDir:   filepath.Join(dataDir, "events"),
		StateDir:    stateDir,
		PauseFile:   filepath.Join(stateDir, "paused"),
		RuntimeFile: filepath.Join(stateDir, "runtime.json"),
	}
}

func Ensure(p Paths) error {
	if err := os.MkdirAll(p.EventsDir, 0o700); err != nil {
		return err
	}
	return os.MkdirAll(p.StateDir, 0o700)
}
