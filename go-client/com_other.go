//go:build !windows

package main

import (
	"errors"
	"os"
	"path/filepath"
)

// AppRecord 在非 Windows 平台仅作占位，保证跨平台编译。
type AppRecord struct {
	Name  string `json:"name"`
	AppID string `json:"appId"`
}

// resolveShortcut 在非 Windows 平台不可用。
func resolveShortcut(lnkPath string) (string, error) {
	return "", errors.New("解析 .lnk 快捷方式仅在 Windows 上支持")
}

// resolveShortcutsBatch 在非 Windows 平台返回空结果。
func resolveShortcutsBatch(lnkPaths []string) []string {
	return make([]string, len(lnkPaths))
}

// enumerateUWPApps 在非 Windows 平台不可用。
func enumerateUWPApps() ([]AppRecord, error) {
	return nil, errors.New("UWP 应用扫描仅在 Windows 上支持")
}

// expandStartMenuRoots 在非 Windows 平台返回空列表。
func expandStartMenuRoots() []string {
	if appData := os.Getenv("APPDATA"); appData != "" {
		return []string{filepath.Join(appData, "Microsoft", "Windows", "Start Menu", "Programs")}
	}
	return nil
}
