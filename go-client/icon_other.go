//go:build !windows

package main

// GetIconBase64 在非 Windows 平台返回空串（无图标）。
func (a *App) GetIconBase64(exePath, lnkPath, sourceType string) string {
	return ""
}
