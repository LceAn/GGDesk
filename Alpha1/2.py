import os
import win32com.client
import time

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# --- 1. 配置项 ---
OUTPUT_FOLDER_NAME = "MyTestShortcuts"
FILENAME_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe',
}

# --- 2. 核心功能 ---
def create_shortcut(target_path, shortcut_path):
    """
    使用 win32com 创建一个 .lnk 快捷方式
    (已移除 print，通过返回值来报告状态)
    """
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.Save()
        return True
    except Exception as e:
        # print(f"    [!] 创建失败: {os.path.basename(shortcut_path)} | 错误: {e}")
        return False

# --- 3. GUI 界面逻辑 ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("快捷方式扫描器 (v4-GUI)")
        # 【新】 增加了窗口高度，为日志区提供空间
        self.root.geometry("600x600") 

        self.found_exes_vars = []

        # --- 顶部：扫描控制 ---
        frame_top = ttk.Frame(root, padding=10)
        frame_top.pack(fill='x')
        
        self.btn_scan = ttk.Button(frame_top, text="1. 选择扫描目录...", command=self.ask_scan_path)
        self.btn_scan.pack(side='left', fill='x', expand=True)

        self.lbl_status = ttk.Label(frame_top, text="请先选择目录")
        self.lbl_status.pack(side='left', padx=10)

        # --- 【新】 问题1解决：显示所选路径 ---
        frame_path = ttk.Frame(root, padding=(10, 0, 10, 5))
        frame_path.pack(fill='x')
        ttk.Label(frame_path, text="所选路径:").pack(side='left')
        self.path_var = tk.StringVar()
        self.entry_path = ttk.Entry(frame_path, textvariable=self.path_var, state='readonly')
        self.entry_path.pack(side='left', fill='x', expand=True, padx=(5, 0))

        # --- 中间：可滚动的复选框列表 ---
        self.st = scrolledtext.ScrolledText(root, wrap=tk.NONE)
        self.st.pack(fill='both', expand=True, padx=10, pady=5)
        self.st.config(state='disabled')
        
        # --- 【新】 问题2解决：日志输出区域 ---
        frame_log = ttk.Frame(root, padding=(10, 5, 10, 5))
        frame_log.pack(fill='x')
        ttk.Label(frame_log, text="--- 日志输出 ---").pack()
        
        self.log_area = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD, state='disabled')
        self.log_area.pack(fill='x', expand=True, padx=10, pady=(0, 5))

        # --- 底部：执行 ---
        frame_bottom = ttk.Frame(root, padding=10)
        frame_bottom.pack(fill='x')
        
        self.btn_create = ttk.Button(frame_bottom, text="2. 生成所选快捷方式", command=self.create_selected_shortcuts, state='disabled')
        self.btn_create.pack(fill='x')

    # 【新】 日志记录函数
    def log(self, message):
        """向 UI 界面中的日志区域追加一条消息"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END) # 自动滚动到底部
        self.log_area.config(state='disabled')
        self.root.update_idletasks() # 强制 UI 刷新

    def ask_scan_path(self):
        """
        弹出对话框让用户选择文件夹
        """
        path_to_scan = filedialog.askdirectory()
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 

        # 【新】 问题1解决：更新路径显示框
        self.path_var.set(path_to_scan)

        self.lbl_status.config(text="正在扫描中...")
        
        # --- 【BUG修复】 问题3解决 ---
        # `self_btn_create` 已修正为 `self.btn_create`
        self.btn_create.config(state='disabled') 
        
        self.log(f"--- 开始扫描: {path_to_scan} ---")
        self.root.update_idletasks()

        # --- 扫描逻辑 ---
        found_exes = []
        for root, dirs, files in os.walk(path_to_scan):
            for file in files:
                if file.lower().endswith(".exe"):
                    if file.lower() not in FILENAME_BLOCKLIST and 'uninstall' not in file.lower():
                        found_exes.append(os.path.join(root, file))
                    else:
                        self.log(f"[自动过滤] 跳过 (黑名单): {file}")
        
        self.log(f"扫描完成。总共找到 {len(found_exes)} 个有效 .exe。")
        self.populate_checklist(found_exes)

    def populate_checklist(self, exes):
        """
        将找到的.exe填充到可滚动的列表中
        """
        # 清空旧内容
        self.st.config(state='normal')
        self.st.delete(1.0, tk.END)
        self.found_exes_vars = []

        if not exes:
            self.lbl_status.config(text="扫描完成，未找到有效 .exe")
            self.st.insert(tk.END, "未找到 .exe 文件。")
            self.st.config(state='disabled')
            return

        # 填充新内容
        for full_path in exes:
            file_name = os.path.basename(full_path)
            var = tk.BooleanVar()
            var.set(True) # 默认全选
            cb = ttk.Checkbutton(self.st, text=file_name, variable=var)
            self.st.window_create("end", window=cb)
            self.st.insert("end", f"  (路径: {os.path.dirname(full_path)})\n") 
            self.found_exes_vars.append((var, file_name, full_path))

        self.lbl_status.config(text=f"找到 {len(exes)} 个 .exe，请勾选：")
        self.st.config(state='disabled')
        self.btn_create.config(state='normal')


    def create_selected_shortcuts(self):
        """
        遍历所有复选框，为被选中的创建快捷方式
        """
        # 1. 确定输出目录
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_dir = os.path.join(desktop_path, OUTPUT_FOLDER_NAME)
        if not os.path.exists(shortcut_dir):
            os.makedirs(shortcut_dir)
            self.log(f"已创建输出文件夹: {shortcut_dir}")

        # 2. 遍历我们保存的变量列表
        created_count = 0
        failed_count = 0
        self.log("--- 开始创建快捷方式 ---")
        
        for (var, file_name, full_path) in self.found_exes_vars:
            if var.get() == True: # 检查复选框是否被勾选
                shortcut_name = f"{os.path.splitext(file_name)[0]}.lnk"
                shortcut_full_path = os.path.join(shortcut_dir, shortcut_name)
                
                # 【新】 问题2解决：在日志区显示创建状态
                if create_shortcut(full_path, shortcut_full_path):
                    self.log(f"[+] 成功: {shortcut_name}")
                    created_count += 1
                else:
                    self.log(f"[!] 失败: {file_name}")
                    failed_count += 1
        
        self.log("--- 操作完成 ---")
        
        # 3. 弹窗反馈结果
        messagebox.showinfo("操作完成", 
                            f"快捷方式已在桌面 '{OUTPUT_FOLDER_NAME}' 文件夹中生成。\n\n"
                            f"成功: {created_count} 个\n"
                            f"失败: {failed_count} 个\n\n"
                            "详细日志请查看主窗口。")
        
        self.lbl_status.config(text="操作完成。可再次扫描。")


# --- 4. 启动主程序 ---

if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 Tkinter 环境。")
    else:
        main_window = tk.Tk()
        app = App(main_window)
        main_window.mainloop()