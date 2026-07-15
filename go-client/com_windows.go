//go:build windows

package main

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	ole "github.com/go-ole/go-ole"
	"github.com/go-ole/go-ole/oleutil"
)

// AppRecord 描述一个 UWP / Microsoft Store 应用。
// Name 为显示名，AppID 为 AUMID（如 Microsoft.WindowsCalculator_8wekyb3d8bbwe!App）。
type AppRecord struct {
	Name  string `json:"name"`
	AppID string `json:"appId"`
}

// resolveShortcut 通过 WScript.Shell 读取 .lnk 的真实目标路径。
// 对应 Python core_discovery.py 中 scan_start_menu 对 TargetPath 的解析。
func resolveShortcut(lnkPath string) (string, error) {
	if _, err := os.Stat(lnkPath); err != nil {
		return "", err
	}

	// 每个调用独立初始化/释放 COM，避免跨线程公寓问题。
	ole.CoInitializeEx(0, ole.COINIT_APARTMENTTHREADED)
	defer ole.CoUninitialize()

	unknown, err := oleutil.CreateObject("WScript.Shell")
	if err != nil {
		return "", fmt.Errorf("创建 WScript.Shell: %w", err)
	}
	defer unknown.Release()

	shell, err := unknown.QueryInterface(ole.IID_IDispatch)
	if err != nil {
		return "", fmt.Errorf("查询 IDispatch: %w", err)
	}
	defer shell.Release()

	// CreateShortcut(lnkPath) -> 返回快捷方式对象。
	// 注意：ToIDispatch() 不增加引用计数，返回的就是 VARIANT 内部同一指针；
	// 因此只 Clear VARIANT（它会 Release），绝不能再 Release 派生的 dispatch，否则 double free。
	scVariant, err := oleutil.CallMethod(shell, "CreateShortcut", lnkPath)
	if err != nil {
		return "", fmt.Errorf("CreateShortcut: %w", err)
	}
	defer scVariant.Clear()

	sc := scVariant.ToIDispatch()
	if sc == nil {
		return "", errors.New("快捷方式对象为空")
	}

	targetVariant, err := oleutil.GetProperty(sc, "TargetPath")
	if err != nil {
		return "", fmt.Errorf("读取 TargetPath: %w", err)
	}
	defer targetVariant.Clear()

	target := strings.TrimSpace(targetVariant.ToString())
	return target, nil
}

// resolveShortcutsBatch 批量解析多个 .lnk，单次 COM 初始化，性能更优。
// 返回每个 lnk 对应的目标路径（解析失败的为空字符串）。
func resolveShortcutsBatch(lnkPaths []string) []string {
	results := make([]string, len(lnkPaths))

	ole.CoInitializeEx(0, ole.COINIT_APARTMENTTHREADED)
	defer ole.CoUninitialize()

	unknown, err := oleutil.CreateObject("WScript.Shell")
	if err != nil {
		return results
	}
	defer unknown.Release()

	shell, err := unknown.QueryInterface(ole.IID_IDispatch)
	if err != nil {
		return results
	}
	defer shell.Release()

	for i, lnk := range lnkPaths {
		if _, err := os.Stat(lnk); err != nil {
			continue
		}
		scVariant, err := oleutil.CallMethod(shell, "CreateShortcut", lnk)
		if err != nil {
			continue
		}
		sc := scVariant.ToIDispatch()
		if sc == nil {
			scVariant.Clear()
			continue
		}
		targetVariant, err := oleutil.GetProperty(sc, "TargetPath")
		if err == nil {
			results[i] = strings.TrimSpace(targetVariant.ToString())
			targetVariant.Clear()
		}
		// 仅 Clear VARIANT（会 Release 内部 dispatch），不再单独 Release sc。
		scVariant.Clear()
	}
	return results
}

// enumerateUWPApps 通过 Shell.Application 枚举 shell:AppsFolder，
// 返回已安装的 UWP / Microsoft Store 应用列表。
// 对应 Python core_discovery.py 的 scan_uwp_apps。
func enumerateUWPApps() ([]AppRecord, error) {
	ole.CoInitializeEx(0, ole.COINIT_APARTMENTTHREADED)
	defer ole.CoUninitialize()

	unknown, err := oleutil.CreateObject("Shell.Application")
	if err != nil {
		return nil, fmt.Errorf("创建 Shell.Application: %w", err)
	}
	defer unknown.Release()

	shell, err := unknown.QueryInterface(ole.IID_IDispatch)
	if err != nil {
		return nil, fmt.Errorf("查询 IDispatch: %w", err)
	}
	defer shell.Release()

	// NameSpace("shell:AppsFolder") -> Folder 对象。
	folderVariant, err := oleutil.CallMethod(shell, "NameSpace", "shell:AppsFolder")
	if err != nil {
		return nil, fmt.Errorf("NameSpace AppsFolder: %w", err)
	}
	defer folderVariant.Clear()

	folder := folderVariant.ToIDispatch()
	if folder == nil {
		return nil, errors.New("AppsFolder 为空")
	}

	// folder.Items() -> FolderItems 集合。
	itemsVariant, err := oleutil.CallMethod(folder, "Items")
	if err != nil {
		return nil, fmt.Errorf("Items: %w", err)
	}
	defer itemsVariant.Clear()

	items := itemsVariant.ToIDispatch()
	if items == nil {
		return nil, errors.New("FolderItems 为空")
	}

	// 通过 Count + Item 逐个枚举（比 ForEach 在 go-ole 里更稳）。
	countVariant, err := oleutil.GetProperty(items, "Count")
	if err != nil {
		return nil, fmt.Errorf("读取 Count: %w", err)
	}
	count := int(countVariant.Val)
	countVariant.Clear()

	apps := []AppRecord{}
	for i := 0; i < count; i++ {
		itemVariant, err := oleutil.GetProperty(items, "Item", i)
		if err != nil {
			continue
		}
		item := itemVariant.ToIDispatch()
		if item == nil {
			itemVariant.Clear()
			continue
		}

		// Name: 显示名（如 "计算器"）。
		// Path: 对 UWP 是 AUMID（如 Microsoft.WindowsCalculator_...!App）。
		name := dispatchString(item, "Name")
		path := dispatchString(item, "Path")

		// 过滤掉非应用条目：UWP 的 Path 通常是 AUMID（不含盘符路径）。
		// 系统残留项（如空名/以 "Microsoft.SharePoint" 之类的框架）会被 AUMID 形态过滤。
		if strings.TrimSpace(name) != "" && strings.TrimSpace(path) != "" {
			// AUMID 形态：PackageFamilyName!AppId，必含 "!"。
			if strings.Contains(path, "!") || strings.HasPrefix(path, "windowsCommunications") {
				apps = append(apps, AppRecord{Name: name, AppID: path})
			}
		}
		// 仅 Clear VARIANT（会 Release 内部 dispatch），不再单独 Release item。
		itemVariant.Clear()
	}
	return apps, nil
}

// dispatchString 安全读取 IDispatch 的字符串属性。
func dispatchString(disp *ole.IDispatch, name string) string {
	if disp == nil {
		return ""
	}
	v, err := oleutil.GetProperty(disp, name)
	if err != nil {
		return ""
	}
	defer v.Clear()
	return v.ToString()
}

// expandStartMenuRoots 返回开始菜单的两个 Program 目录（用户级 + 系统级）。
func expandStartMenuRoots() []string {
	roots := []string{}
	programData := os.Getenv("ProgramData")
	if programData != "" {
		roots = append(roots, filepath.Join(programData, "Microsoft", "Windows", "Start Menu", "Programs"))
	}
	appData := os.Getenv("APPDATA")
	if appData != "" {
		roots = append(roots, filepath.Join(appData, "Microsoft", "Windows", "Start Menu", "Programs"))
	}
	return roots
}
