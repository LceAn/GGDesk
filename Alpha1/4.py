import os
import win32com.client
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from collections import defaultdict
import re

# --- 1. 配置项 ---
OUTPUT_FOLDER_NAME = "MyTestShortcuts"
# 【新】黑名单改为文件名，程序启动时从 blocklist.txt 读取
FILENAME_BLOCKLIST_FILE = "blocklist.txt"
DEFAULT_BLOCKLIST = {
    'uninstall.exe', 'unins000.exe', 'unins001.exe', 'unins002.exe',
    'setup.exe', 'install.exe', 'update.exe', 'updater.exe',
    'vcredist_x64.exe', 'vcredist_x86.exe', 'vc_redist.x64.exe', 'vc_redist.x86.exe',
    'crashpad_handler.exe', 'errorreporter.exe', 'report.exe',
}

# --- 2. 核心功能 (无修改) ---
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

# --- 3. 【新】Stage 2 (详情) 弹窗 ---
class RefineWindow(tk.Toplevel):
    """
    "Stage 2" 弹窗: 单个程序的 .exe 精细选择器
    """
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(f"详情: {program_data['name']}")
        self.geometry("700x500")

        self.program_data = program_data
        # all_exes 格式: [(full_path, file_name, size_bytes, relative_path), ...]
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes'])
        
        self.build_ui()
        self.populate_tree()
        self.pre_select_items()

    def build_ui(self):
        # --- 筛选 ---
        frame_filter = ttk.Frame(self, padding=(10, 10, 10, 0))
        frame_filter.pack(fill='x')
        ttk.Label(frame_filter, text="筛选:").pack(side='left')
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self.on_filter_changed)
        ttk.Entry(frame_filter, textvariable=self.filter_var).pack(fill='x', expand=True, padx=5)

        # --- 列表 (Treeview) ---
        frame_tree = ttk.Frame(self, padding=10)
        frame_tree.pack(fill='both', expand=True)
        
        cols = ('name', 'size', 'path')
        self.tree = ttk.Treeview(frame_tree, columns=cols, show='headings', selectmode='extended')
        
        # 定义列
        self.tree.heading('name', text='程序名', command=lambda: self.sort_column('name', False))
        self.tree.heading('size', text='大小', command=lambda: self.sort_column('size', False))
        self.tree.heading('path', text='相对路径', command=lambda: self.sort_column('path', False))
        
        self.tree.column('name', width=200, stretch=tk.YES)
        self.tree.column('size', width=100, stretch=tk.NO, anchor='e')
        self.tree.column('path', width=350, stretch=tk.YES)
        
        # 滚动条
        ysb = ttk.Scrollbar(frame_tree, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(frame_tree, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        
        ysb.pack(side='right', fill='y')
        xsb.pack(side='bottom', fill='x')
        self.tree.pack(fill='both', expand=True)

        # --- 底部按钮 ---
        frame_bottom = ttk.Frame(self, padding=10)
        frame_bottom.pack(fill='x')
        
        self.btn_ok = ttk.Button(frame_bottom, text="确认", command=self.on_ok)
        self.btn_ok.pack(side='right')
        
        self.btn_cancel = ttk.Button(frame_bottom, text="取消", command=self.on_cancel)
        self.btn_cancel.pack(side='right', padx=10)
        
        self.btn_all = ttk.Button(frame_bottom, text="全选 (可见)", command=self.select_all_visible)
        self.btn_all.pack(side='left')
        
        self.btn_none = ttk.Button(frame_bottom, text="全不选", command=self.select_none)
        self.btn_none.pack(side='left', padx=10)

    def populate_tree(self):
        """填充 Treeview 列表"""
        for (full_path, file_name, size_bytes, relative_path) in self.all_exes:
            size_mb = f"{size_bytes / (1024*1024):.2f} MB"
            # 插入数据，'item' 的 'values' 用于显示，'item' 的 'iid' (item id) 我们设为 full_path
            self.tree.insert('', 'end', iid=full_path, values=(file_name, size_mb, relative_path))
            
            # 【重要】存储原始数据以便排序
            self.tree.set(full_path, 'size', size_bytes) # 'size' 列存储的是原始字节数

    def pre_select_items(self):
        """根据传入的 selected_exes 预先选中行"""
        for full_path in self.original_selection:
            if self.tree.exists(full_path):
                self.tree.selection_add(full_path)

    def on_filter_changed(self, *args):
        """实时筛选 Treeview"""
        query = self.filter_var.get().lower()
        # 先分离所有子节点
        children = self.tree.get_children('')
        for item_id in children:
            self.tree.detach(item_id)
        
        # 重新附加匹配的节点
        for item_id in children:
            values = self.tree.item(item_id, 'values')
            # 检查文件名和路径是否匹配
            if query in values[0].lower() or query in values[2].lower():
                self.tree.move(item_id, '', 'end')

    def sort_column(self, col, reverse):
        """列排序功能"""
        # 从 Treeview 中获取数据
        # `l` 是一个元组列表: [(item_value, item_id), ...]
        l = []
        for item_id in self.tree.get_children(''):
            # self.tree.set(item_id, col) 会获取我们之前存的 *原始* 数据
            l.append((self.tree.set(item_id, col), item_id))

        # 根据数据类型排序
        if col == 'size':
            # 按数字排序
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        else:
            # 按字符串排序
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)

        # 重新插入排序后的 item
        for i, (val, item_id) in enumerate(l):
            self.tree.move(item_id, '', i)

        # 切换排序方向
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def select_all_visible(self):
        """全选当前可见 (未被过滤掉) 的项"""
        self.select_none()
        visible_items = self.tree.get_children('')
        for item_id in visible_items:
            self.tree.selection_add(item_id)
            
    def select_none(self):
        self.tree.selection_set() # 清空所有选择

    def on_ok(self):
        """保存选择并关闭"""
        # self.tree.selection() 返回被选中项的 iid (即 full_path)
        self.program_data['selected_exes'] = self.tree.selection()
        self.destroy()

    def on_cancel(self):
        """不保存，直接关闭"""
        self.destroy()

# --- 4. 【新】Stage 1 (主窗口) 应用 ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("快捷方式扫描器 (v7-Discovery)")
        self.root.geometry("800x600") 

        # 存储被发现的程序: [{ 'name': ..., 'root_path': ..., 'all_exes': [...], 'selected_exes': [...] }, ...]
        self.programs = []
        
        self.load_blocklist()

        # --- 顶部：扫描控制 ---
        frame_top = ttk.Frame(root, padding=10)
        frame_top.pack(fill='x')
        
        self.btn_scan = ttk.Button(frame_top, text="1. 选择扫描目录...", command=self.ask_scan_path)
        self.btn_scan.pack(side='left', fill='x', expand=True, ipady=4)

        self.btn_blocklist = ttk.Button(frame_top, text="管理黑名单", command=self.show_blocklist)
        self.btn_blocklist.pack(side='left', padx=(10, 0))

        # --- 路径显示 ---
        frame_path = ttk.Frame(root, padding=(10, 0, 10, 5))
        frame_path.pack(fill='x')
        ttk.Label(frame_path, text="所选路径:").pack(side='left')
        self.path_var = tk.StringVar()
        self.entry_path = ttk.Entry(frame_path, textvariable=self.path_var, state='readonly')
        self.entry_path.pack(side='left', fill='x', expand=True, padx=(5, 0))

        # --- 【新】Stage 1: 程序发现列表 ---
        frame_tree = ttk.Frame(root, padding=10)
        frame_tree.pack(fill='both', expand=True)
        
        cols = ('name', 'status', 'path')
        self.tree = ttk.Treeview(frame_tree, columns=cols, show='headings', selectmode='browse')
        
        self.tree.heading('name', text='发现的程序')
        self.tree.heading('status', text='当前选择')
        self.tree.heading('path', text='程序根目录')
        
        self.tree.column('name', width=200, stretch=tk.NO)
        self.tree.column('status', width=200, stretch=tk.NO)
        self.tree.column('path', width=350, stretch=tk.YES)
        
        ysb = ttk.Scrollbar(frame_tree, orient='vertical', command=self.tree.yview)
        ysb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.pack(fill='both', expand=True)
        
        # 绑定行选择事件
        self.tree.bind('<<TreeviewSelect>>', self.on_program_select)

        # --- 中间按钮 ---
        frame_actions = ttk.Frame(root, padding=10)
        frame_actions.pack(fill='x')

        self.btn_refine = ttk.Button(frame_actions, text="2. 详情/修改选择...", command=self.open_refine_window, state='disabled')
        self.btn_refine.pack(side='left')

        # --- 底部：执行按钮 ---
        frame_bottom = ttk.Frame(root, padding=10)
        frame_bottom.pack(fill='x')
        
        self.btn_create = ttk.Button(frame_bottom, text="3. 生成所有快捷方式", command=self.generate_shortcuts, state='disabled')
        self.btn_create.pack(fill='x', ipady=4)

        # --- 日志区 ---
        frame_log = ttk.Frame(root, padding=(10, 5, 10, 5))
        frame_log.pack(fill='x')
        ttk.Label(frame_log, text="--- 日志输出 ---").pack()
        
        self.log_area = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD, state='disabled')
        self.log_area.pack(fill='x', expand=True, padx=10, pady=(0, 5))
        
        self.log(f"程序已启动。黑名单已从 {FILENAME_BLOCKLIST_FILE} 加载。")
        self.log("请选择一个目录进行“程序发现”。")

    # --- 日志 ---
    def log(self, message):
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update_idletasks() 

    # --- 黑名单管理 ---
    def load_blocklist(self):
        self.blocklist = set(DEFAULT_BLOCKLIST)
        if os.path.exists(FILENAME_BLOCKLIST_FILE):
            try:
                with open(FILENAME_BLOCKLIST_FILE, 'r') as f:
                    for line in f:
                        if line.strip():
                            self.blocklist.add(line.strip().lower())
            except Exception as e:
                self.log(f"[!] 加载 {FILENAME_BLOCKLIST_FILE} 失败: {e}")
        else:
            self.save_blocklist() # 创建一个默认的
            
    def save_blocklist(self):
        try:
            with open(FILENAME_BLOCKLIST_FILE, 'w') as f:
                for item in sorted(self.blocklist):
                    f.write(f"{item}\n")
            return True
        except Exception as e:
            messagebox.showerror("保存失败", f"无法写入 {FILENAME_BLOCKLIST_FILE}:\n{e}")
            return False

    def show_blocklist(self):
        popup = tk.Toplevel(self.root)
        popup.title("管理黑名单")
        popup.geometry("400x300")
        popup.transient(self.root)
        popup.grab_set()

        lbl = ttk.Label(popup, text="每行一个文件名 (不区分大小写):", padding=10)
        lbl.pack()
        
        text_area = scrolledtext.ScrolledText(popup, height=10, wrap=tk.WORD, state='normal')
        text_area.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        for item in sorted(self.blocklist):
            text_area.insert(tk.END, f"{item}\n")
        
        frame_btns = ttk.Frame(popup, padding=10)
        frame_btns.pack(fill='x')

        def on_save():
            new_list = set(text_area.get(1.0, tk.END).split('\n'))
            self.blocklist = {item.lower() for item in new_list if item.strip()}
            if self.save_blocklist():
                self.log("[+] 黑名单已保存。")
                popup.destroy()
        
        btn_save = ttk.Button(frame_btns, text="保存并关闭", command=on_save)
        btn_save.pack(side='right')
        btn_cancel = ttk.Button(frame_btns, text="取消", command=popup.destroy)
        btn_cancel.pack(side='right', padx=10)

    # --- 核心 v7 扫描逻辑 ---
    def ask_scan_path(self):
        path_to_scan = filedialog.askdirectory()
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 
        self.path_var.set(path_to_scan)
        self.log(f"--- 开始程序发现: {path_to_scan} ---")
        self.root.update_idletasks()
        
        self.programs = self.discover_programs(path_to_scan)
        self.populate_main_treeview()
        
        self.log(f"--- 发现完成 ---")
        self.log(f"总共发现 {len(self.programs)} 个潜在程序组。")
        self.btn_create.config(state='normal' if self.programs else 'disabled')

    def discover_programs(self, scan_path):
        """
        v7 核心算法：程序发现
        """
        # 1. 递归扫描，收集所有 .exe 及其文件夹
        exe_folders = defaultdict(list)
        all_exes_data = {} # 存储 (full_path, file_name, size_bytes, relative_path)
        
        for root, dirs, files in os.walk(scan_path, topdown=True):
            current_exes = []
            for file in files:
                if file.lower().endswith(".exe"):
                    if file.lower() in self.blocklist:
                        self.log(f"[过滤] {os.path.join(root, file)}")
                        continue
                    
                    try:
                        full_path = os.path.join(root, file)
                        size_bytes = os.path.getsize(full_path)
                        current_exes.append(full_path)
                        # 存储 .exe 的详细数据，以 full_path 为键
                        all_exes_data[full_path] = (full_path, file, size_bytes, os.path.relpath(root, scan_path))
                    except (IOError, OSError) as e:
                        self.log(f"[!] 无法访问: {file} | {e}")
                        
            if current_exes:
                exe_folders[root] = current_exes

        if not exe_folders:
            self.log("未找到任何 (未被过滤的) .exe 文件。")
            return []

        # 2. 找到“顶层”的 .exe 文件夹 (过滤掉子文件夹)
        sorted_folders = sorted(exe_folders.keys())
        top_level_folders = []
        if sorted_folders:
            last_folder = sorted_folders[0]
            top_level_folders.append(last_folder)
            for current_folder in sorted_folders[1:]:
                # 如果当前文件夹不是上一个文件夹的子目录
                if not current_folder.startswith(last_folder + os.path.sep):
                    top_level_folders.append(current_folder)
                    last_folder = current_folder
        
        self.log(f"发现 {len(top_level_folders)} 个顶层 .exe 目录...")

        # 3. 确定“程序根目录” (bin 逻辑)
        program_groups = defaultdict(list) # 'program_root' -> [exe_full_path, ...]
        program_roots = {} # 'program_root' -> 'program_name'
        
        for folder in top_level_folders:
            folder_name = os.path.basename(folder)
            if folder_name.lower() == 'bin':
                program_root = os.path.dirname(folder)
                program_name = os.path.basename(program_root)
            else:
                program_root = folder
                program_name = folder_name
            
            # 解决根目录冲突 (e.g., .../bin 和 .../bin/clang)
            # 我们只保留最顶层的根
            is_subpath = False
            for existing_root in list(program_roots.keys()):
                if program_root.startswith(existing_root + os.path.sep):
                    is_subpath = True
                    break # 它是子目录，不用管
                if existing_root.startswith(program_root + os.path.sep):
                    # 发现了更顶层的根，替换掉旧的
                    del program_roots[existing_root]
            
            if not is_subpath:
                program_roots[program_root] = program_name

        # 4. 将所有 .exe 分配到它们所属的“程序根目录”
        for full_path in all_exes_data.keys():
            matching_root = None
            for root in program_roots.keys():
                if full_path.startswith(root + os.path.sep):
                    if matching_root is None or len(root) > len(matching_root):
                        matching_root = root
            if matching_root:
                program_groups[matching_root].append(full_path)

        # 5. 格式化最终数据，并运行 v6 启发式
        final_programs = []
        for root, exe_paths in program_groups.items():
            name = program_roots[root]
            # 运行 v6 启发式 (文件夹名匹配)
            suggested_exes = self.run_v6_heuristic(name, exe_paths)
            
            program_data = {
                'name': name,
                'root_path': root,
                'all_exes': [all_exes_data[path] for path in exe_paths], # [(full_path, ...), ...]
                'selected_exes': tuple(suggested_exes) # 设为元组，以便在 RefineWindow 中比较
            }
            final_programs.append(program_data)
        
        return sorted(final_programs, key=lambda p: p['name'])

    def run_v6_heuristic(self, program_name, exe_paths):
        """v6 启发式：基于文件夹名的匹配"""
        # 清理程序名，获取关键字
        keywords = set(re.split(r'[_\-\s\d.]+', program_name.lower()))
        keywords.discard('')
        
        if not keywords: # e.g., 文件夹叫 "123"
            return []
            
        suggestions = []
        for path in exe_paths:
            exe_name = os.path.basename(path).lower()
            for key in keywords:
                if key in exe_name:
                    suggestions.append(path)
                    break # 匹配一个就行
        
        # 优先选择最短的匹配项 (e.g., "clion64.exe" 优于 "clion-clang-tidy.exe")
        suggestions.sort(key=len)
        return suggestions[:1] # 只建议最好的 1 个

    def populate_main_treeview(self):
        """填充 Stage 1 的程序列表"""
        self.tree.delete(*self.tree.get_children())
        
        for i, prog_data in enumerate(self.programs):
            # iid 设为行索引
            iid = str(i) 
            status_text = self.get_program_status_text(prog_data)
            self.tree.insert('', 'end', iid=iid, values=(prog_data['name'], status_text, prog_data['root_path']))

    def get_program_status_text(self, prog_data):
        """获取显示在 "Status" 列的文本"""
        count = len(prog_data['selected_exes'])
        if count == 0:
            return "(未选择)"
        elif count == 1:
            return os.path.basename(prog_data['selected_exes'][0])
        else:
            return f"({count} 个文件已选)"

    def on_program_select(self, event):
        """当用户在主列表选择一行时"""
        if self.tree.selection():
            self.btn_refine.config(state='normal')
        else:
            self.btn_refine.config(state='disabled')

    def open_refine_window(self):
        """打开 Stage 2 详情弹窗"""
        selected_item_id = self.tree.selection()
        if not selected_item_id:
            return
        
        # 从 iid (行索引) 获取程序数据
        program_index = int(selected_item_id[0])
        program_data = self.programs[program_index]
        
        self.log(f"--- 打开详情: {program_data['name']} ---")
        
        # 启动弹窗
        refine_win = RefineWindow(self.root, program_data)
        # 等待弹窗关闭
        self.root.wait_window(refine_win)
        
        self.log("--- 详情窗口已关闭 ---")
        
        # 弹窗关闭后，刷新主列表中的 "Status" 列
        status_text = self.get_program_status_text(program_data)
        self.tree.item(selected_item_id[0], values=(program_data['name'], status_text, program_data['root_path']))

    def generate_shortcuts(self):
        """最终生成快捷方式"""
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_dir = os.path.join(desktop_path, OUTPUT_FOLDER_NAME)
        if not os.path.exists(shortcut_dir):
            os.makedirs(shortcut_dir)
            self.log(f"已创建输出文件夹: {shortcut_dir}")

        total_created = 0
        total_failed = 0
        self.log("--- 开始批量创建快捷方式 ---")
        
        for program in self.programs:
            if not program['selected_exes']:
                continue
                
            self.log(f"  正在处理程序: {program['name']}")
            for full_path in program['selected_exes']:
                file_name = os.path.basename(full_path)
                shortcut_name = f"{os.path.splitext(file_name)[0]}.lnk"
                shortcut_full_path = os.path.join(shortcut_dir, shortcut_name)
                
                if create_shortcut(full_path, shortcut_full_path):
                    self.log(f"    [+] 成功: {shortcut_name}")
                    total_created += 1
                else:
                    self.log(f"    [!] 失败: {file_name}")
                    total_failed += 1
        
        self.log("--- 全部处理完成 ---")
        messagebox.showinfo("操作完成", 
                            f"操作已在桌面 '{OUTPUT_FOLDER_NAME}' 文件夹中完成。\n\n"
                            f"成功: {total_created} 个\n"
                            f"失败: {total_failed} 个\n\n"
                            "详细日志请查看主窗口。")

# --- 5. 启动主程序 ---
if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 Tkinter 环境。")
    else:
        main_window = tk.Tk()
        app = App(main_window)
        main_window.mainloop()