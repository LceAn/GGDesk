# scanner_backend/utils_system.py
import os
import win32com.client

def create_shortcut(target_path, shortcut_path, args=""):
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        # UWP 逻辑
        if "://" not in target_path and ":" not in target_path and "\\" not in target_path and "shell:AppsFolder" in args:
             shortcut.TargetPath = "explorer.exe"
             shortcut.Arguments = args
             shortcut.IconLocation = "explorer.exe,0"
        else:
            shortcut.TargetPath = target_path
            if os.path.exists(target_path):
                shortcut.WorkingDirectory = os.path.dirname(target_path)
            shortcut.IconLocation = target_path
        shortcut.Save()
        return True, f"成功: {os.path.basename(shortcut_path)}"
    except Exception as e:
        return False, f"失败: {os.path.basename(shortcut_path)} | {e}"

def open_file_explorer(path):
    if not os.path.exists(path): return
    try: os.startfile(path)
    except Exception as e: print(f"无法打开文件夹: {e}")

def scan_existing_shortcuts(folder_path):
    results = []
    if not os.path.exists(folder_path): return results
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        for file in os.listdir(folder_path):
            if file.lower().endswith(".lnk"):
                full_path = os.path.join(folder_path, file)
                try:
                    shortcut = shell.CreateShortCut(full_path)
                    results.append((file, shortcut.TargetPath))
                except:
                    results.append((file, "无法读取目标"))
    except: pass
    return results

def normalize_path(path):
    if not path: return ""
    return os.path.normpath(os.path.abspath(path)).lower()