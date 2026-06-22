package main

import (
	"os"
	"path/filepath"
)

const defaultOutputFolderName = "MyTestShortcuts"

func projectRoot() string {
	wd, err := os.Getwd()
	if err != nil {
		return "."
	}
	dir := wd
	for i := 0; i < 8; i++ {
		if _, err := os.Stat(filepath.Join(dir, "data", "user_data.db")); err == nil {
			return dir
		}
		if _, err := os.Stat(filepath.Join(dir, "config", "config.ini")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	if filepath.Base(wd) == "go-client" {
		return filepath.Dir(wd)
	}
	return wd
}

func configDir() string {
	return filepath.Join(projectRoot(), "config")
}

func dataDir() string {
	return filepath.Join(projectRoot(), "data")
}

func configFilePath() string {
	return filepath.Join(configDir(), "config.ini")
}

func userDatabasePath() string {
	return filepath.Join(dataDir(), "user_data.db")
}

func cacheDatabasePath() string {
	return filepath.Join(dataDir(), "cache.db")
}

func desktopDefaultOutputPath() string {
	if userProfile := os.Getenv("USERPROFILE"); userProfile != "" {
		return filepath.Join(userProfile, "Desktop", defaultOutputFolderName)
	}
	home, err := os.UserHomeDir()
	if err == nil {
		return filepath.Join(home, "Desktop", defaultOutputFolderName)
	}
	return filepath.Join(projectRoot(), defaultOutputFolderName)
}
