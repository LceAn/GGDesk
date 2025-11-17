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
    try:
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_path
        shortcut.WorkingDirectory = os.path.dirname(target_path)
        shortcut.IconLocation = target_path
        shortcut.Save()
        return True
    except Exception as e:
        return False

# --- 3. GUI 界面逻辑 ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("快捷方式扫描器 (v5-功能版)")
        self.root.geometry("600x600") 

        self.found_exes_vars = []

        # --- 顶部：扫描控制 ---
        frame_top = ttk.Frame(root, padding=10)
        frame_top.pack(fill='x')
        
        self.btn_scan = ttk.Button(frame_top, text="1. 选择扫描目录...", command=self.ask_scan_path)
        self.btn_scan.pack(side='left', fill='x', expand=True, ipady=4) # 增加按钮高度

        # 【新】 问题4：查看黑名单按钮
        self.btn_blocklist = ttk.Button(frame_top, text="查看黑名单", command=self.show_blocklist)
        self.btn_blocklist.pack(side='left', padx=(10, 0))

        # --- 路径显示 ---
        frame_path = ttk.Frame(root, padding=(10, 0, 10, 5))
        frame_path.pack(fill='x')
        ttk.Label(frame_path, text="所选路径:").pack(side='left')
        self.path_var = tk.StringVar()
        self.entry_path = ttk.Entry(frame_path, textvariable=self.path_var, state='readonly')
        self.entry_path.pack(side='left', fill='x', expand=True, padx=(5, 0))

        # --- 【新】 问题2：全选/反选与统计 ---
        frame_select = ttk.Frame(root, padding=(10, 5, 10, 0))
        frame_select.pack(fill='x')
        
        self.btn_select_all = ttk.Button(frame_select, text="全选", command=self.select_all, state='disabled')
        self.btn_select_all.pack(side='left')
        
        self.btn_deselect_all = ttk.Button(frame_select, text="全不选", command=self.deselect_all, state='disabled')
        self.btn_deselect_all.pack(side='left', padx=5)

        self.lbl_count_var = tk.StringVar()
        self.lbl_count_var.set("已选 0 / 总共 0")
        self.lbl_count = ttk.Label(frame_select, textvariable=self.lbl_count_var)
        self.lbl_count.pack(side='right')

        # --- 中间：可滚动的复选框列表 ---
        self.st = scrolledtext.ScrolledText(root, wrap=tk.NONE)
        self.st.pack(fill='both', expand=True, padx=10, pady=5)
        self.st.config(state='disabled')

        # --- 底部：执行按钮 ---
        frame_bottom = ttk.Frame(root, padding=10)
        frame_bottom.pack(fill='x')
        
        self.btn_create = ttk.Button(frame_bottom, text="2. 生成所选快捷方式", command=self.create_selected_shortcuts, state='disabled')
        self.btn_create.pack(fill='x', ipady=4) # 增加按钮高度

        # --- 【新】 问题1：布局调整，日志区在最底部 ---
        frame_log = ttk.Frame(root, padding=(10, 5, 10, 5))
        frame_log.pack(fill='x')
        ttk.Label(frame_log, text="--- 日志输出 ---").pack()
        
        self.log_area = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD, state='disabled')
        self.log_area.pack(fill='x', expand=True, padx=10, pady=(0, 5))
        
        # 初始日志
        self.log("程序已启动。请选择一个目录进行扫描。")

    def log(self, message):
        """向 UI 界面中的日志区域追加一条消息"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END) # 自动滚动到底部
        self.log_area.config(state='disabled')
        self.root.update_idletasks() 

    def ask_scan_path(self):
        """
        弹出对话框让用户选择文件夹
        """
        path_to_scan = filedialog.askdirectory()
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 

        self.path_var.set(path_to_scan)
        self.btn_create.config(state='disabled') 
        self.btn_select_all.config(state='disabled')
        self.btn_deselect_all.config(state='disabled')
        self.log(f"--- 开始扫描: {path_to_scan} ---")

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
        self.st.config(state='normal')
        self.st.delete(1.0, tk.END)
        self.found_exes_vars = []

        if not exes:
            self.st.insert(tk.END, "未找到 .exe 文件。")
            self.st.config(state='disabled')
            self.update_count() # 更新计数为 0/0
            return

        # 填充新内容
        for full_path in exes:
            file_name = os.path.basename(full_path)
            var = tk.BooleanVar()
            var.set(True) # 默认全选
            
            # 【新】 问题2：绑定更新计数的命令
            # 当用户点击复选框时，自动调用 self.update_count
            cb = ttk.Checkbutton(self.st, text=file_name, variable=var, command=self.update_count)
            
            self.st.window_create("end", window=cb)
            self.st.insert("end", f"  (路径: {os.path.dirname(full_path)})\n") 
            self.found_exes_vars.append((var, file_name, full_path))

        self.st.config(state='disabled')
        self.btn_create.config(state='normal')
        self.btn_select_all.config(state='normal')
        self.btn_deselect_all.config(state='normal')
        self.update_count() # 填充完毕后，更新一次计数

    # --- 【新】 问题2：全选/全不选/计数 的功能函数 ---
    def update_count(self):
        """更新“已选/总共”的标签"""
        total = len(self.found_exes_vars)
        selected = 0
        for (var, _, _) in self.found_exes_vars:
            if var.get() == True:
                selected += 1
        self.lbl_count_var.set(f"已选 {selected} / 总共 {total}")

    def select_all(self):
        """设置所有复选框为 True"""
        for (var, _, _) in self.found_exes_vars:
            var.set(True)
        self.update_count() # 更新计数

    def deselect_all(self):
        """设置所有复选框为 False"""
        for (var, _, _) in self.found_exes_vars:
            var.set(False)
        self.update_count() # 更新计数
        
    # --- 【新】 问题4：显示黑名单的功能函数 ---
    def show_blocklist(self):
        """弹出一个新窗口显示黑名单"""
        # 创建一个 Toplevel 窗口 (弹窗)
        popup = tk.Toplevel(self.root)
        popup.title("内置黑名单")
        popup.geometry("400x300")
        
        # 设置弹窗总是在主窗口之上
        popup.transient(self.root) 
        popup.grab_set()

        lbl = ttk.Label(popup, text="程序会自动过滤以下文件名 (不区分大小写):", padding=10)
        lbl.pack()
        
        # 使用可滚动文本框显示列表
        log_area = scrolledtext.ScrolledText(popup, height=10, wrap=tk.WORD, state='normal')
        log_area.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # 填充内容
        for item in sorted(FILENAME_BLOCKLIST):
            log_area.insert(tk.END, f"{item}\n")
            
        log_area.config(state='disabled') # 设为只读
        
        # 添加关闭按钮
        btn_close = ttk.Button(popup, text="关闭", command=popup.destroy)
        btn_close.pack(pady=10)

    def create_selected_shortcuts(self):
        """
        遍历所有复选框，为被选中的创建快捷方式
        """
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_dir = os.path.join(desktop_path, OUTPUT_FOLDER_NAME)
        if not os.path.exists(shortcut_dir):
            os.makedirs(shortcut_dir)
            self.log(f"已创建输出文件夹: {shortcut_dir}")

        created_count = 0
        failed_count = 0
        self.log("--- 开始创建快捷方式 ---")
        
        for (var, file_name, full_path) in self.found_exes_vars:
            if var.get() == True: 
                shortcut_name = f"{os.path.splitext(file_name)[0]}.lnk"
                shortcut_full_path = os.path.join(shortcut_dir, shortcut_name)
                
                if create_shortcut(full_path, shortcut_full_path):
                    self.log(f"[+] 成功: {shortcut_name}")
                    created_count += 1
                else:
                    self.log(f"[!] 失败: {file_name}")
                    failed_count += 1
        
        self.log("--- 操作完成 ---")
        messagebox.showinfo("操作完成", 
                            f"操作已在桌面 '{OUTPUT_FOLDER_NAME}' 文件夹中完成。\n\n"
                            f"成功: {created_count} 个\n"
                            f"失败: {failed_count} 个\n\n"
                            "详细日志请查看主窗口。")
        

# --- 4. 启动主程序 ---
if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 Tkinter 环境。")
    else:
        main_window = tk.Tk()
        app = App(main_window)
        main_window.mainloop()