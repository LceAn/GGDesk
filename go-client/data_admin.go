package main

import (
	"io"
	"os"
	"path/filepath"
	"time"
)

type BackupReport struct {
	Path string `json:"path"`
	Size int64  `json:"size"`
}

func (a *App) BackupDatabase() (BackupReport, error) {
	if err := a.ensureDB(); err != nil {
		return BackupReport{}, err
	}
	backupDir := filepath.Join(dataDir(), "backups")
	if err := os.MkdirAll(backupDir, 0755); err != nil {
		return BackupReport{}, err
	}
	name := "user_data_" + time.Now().Format("20060102_150405") + ".db"
	dest := filepath.Join(backupDir, name)
	if err := copyFile(a.dbPath, dest); err != nil {
		return BackupReport{}, err
	}
	info, err := os.Stat(dest)
	if err != nil {
		return BackupReport{}, err
	}
	return BackupReport{Path: dest, Size: info.Size()}, nil
}

func (a *App) ResetDatabase() error {
	a.mu.Lock()
	if a.db != nil {
		_ = a.db.Close()
		a.db = nil
	}
	dbPath := a.dbPath
	if dbPath == "" {
		dbPath = userDatabasePath()
	}
	a.mu.Unlock()

	if err := os.Remove(dbPath); err != nil && !os.IsNotExist(err) {
		return err
	}
	return a.ensureDB()
}

func copyFile(src, dest string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer out.Close()
	if _, err := io.Copy(out, in); err != nil {
		return err
	}
	return out.Sync()
}
