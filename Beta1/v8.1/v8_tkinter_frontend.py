import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# --- 导入我们全新的后端逻辑 ---
import scanner_backend as backend

# --- Stage 2 (详情) 弹窗 (无变化，纯 UI) ---
class RefineWindow(tk.Toplevel):
    def __init__(self, parent, program_data):
        super().__init__(parent)
        self.transient(parent)
        self.grab_set()
        self.title(f"详情: {program_data['name']}")
        self.geometry("700x500")

        self.program_data = program_data
        self.all_exes = program_data['all_exes']
        self.original_selection = set(program_data['selected_exes'])
        
        self.build_ui()
        self.populate_tree()
        self.pre_select_items()

    def build_ui(self):
        frame_filter = ttk.Frame(self, padding=(10, 10, 10, 0))
        frame_filter.pack(fill='x')
        ttk.Label(frame_filter, text="筛选:").pack(side='left')
        self.filter_var = tk.StringVar()
        self.filter_var.trace("w", self.on_filter_changed)
        ttk.Entry(frame_filter, textvariable=self.filter_var).pack(fill='x', expand=True, padx=5)

        frame_tree = ttk.Frame(self, padding=10)
        frame_tree.pack(fill='both', expand=True)
        
        cols = ('name', 'size', 'path')
        self.tree = ttk.Treeview(frame_tree, columns=cols, show='headings', selectmode='extended')
        
        self.tree.heading('name', text='程序名', command=lambda: self.sort_column('name', False))
        self.tree.heading('size', text='大小', command=lambda: self.sort_column('size', False))
        self.tree.heading('path', text='相对路径', command=lambda: self.sort_column('path', False))
        
        self.tree.column('name', width=200, stretch=tk.YES)
        self.tree.column('size', width=100, stretch=tk.NO, anchor='e')
        self.tree.column('path', width=350, stretch=tk.YES)
        
        ysb = ttk.Scrollbar(frame_tree, orient='vertical', command=self.tree.yview)
        xsb = ttk.Scrollbar(frame_tree, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        
        ysb.pack(side='right', fill='y')
        xsb.pack(side='bottom', fill='x')
        self.tree.pack(fill='both', expand=True)

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
        for (full_path, file_name, size_bytes, relative_path) in self.all_exes:
            size_mb = f"{size_bytes / (1024*1024):.2f} MB"
            self.tree.insert('', 'end', iid=full_path, values=(file_name, size_mb, relative_path))
            self.tree.set(full_path, 'size', size_bytes) 

    def pre_select_items(self):
        for full_path in self.original_selection:
            if self.tree.exists(full_path):
                self.tree.selection_add(full_path)

    def on_filter_changed(self, *args):
        query = self.filter_var.get().lower()
        children = self.tree.get_children('')
        for item_id in children:
            self.tree.detach(item_id)
        for item_id in children:
            values = self.tree.item(item_id, 'values')
            if query in values[0].lower() or query in values[2].lower():
                self.tree.move(item_id, '', 'end')

    def sort_column(self, col, reverse):
        l = []
        for item_id in self.tree.get_children(''):
            l.append((self.tree.set(item_id, col), item_id))
        if col == 'size':
            l.sort(key=lambda t: int(t[0]), reverse=reverse)
        else:
            l.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for i, (val, item_id) in enumerate(l):
            self.tree.move(item_id, '', i)
        self.tree.heading(col, command=lambda: self.sort_column(col, not reverse))

    def select_all_visible(self):
        self.select_none()
        visible_items = self.tree.get_children('')
        for item_id in visible_items:
            self.tree.selection_add(item_id)
            
    def select_none(self):
        self.tree.selection_set()

    def on_ok(self):
        self.program_data['selected_exes'] = self.tree.selection()
        self.destroy()

    def on_cancel(self):
        self.destroy()

# --- Stage 1 (主窗口) 应用 ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("快捷方式扫描器 (v8.1-Tkinter)")
        
        # 【新】v8.1 加载配置
        self.config = backend.load_config()
        # 【新】v8.1 设置窗口大小和位置
        geometry = self.config.get('Settings', 'window_geometry', fallback='800x600')
        self.root.geometry(geometry)
        
        self.programs = []
        
        # 【新】v8.1 加载黑名单
        self.blocklist, msg = backend.load_blocklist()

        # --- UI 布局 ---
        frame_top = ttk.Frame(root, padding=10)
        frame_top.pack(fill='x')
        self.btn_scan = ttk.Button(frame_top, text="1. 选择扫描目录...", command=self.ask_scan_path)
        self.btn_scan.pack(side='left', fill='x', expand=True, ipady=4)
        self.btn_blocklist = ttk.Button(frame_top, text="管理黑名单", command=self.show_blocklist)
        self.btn_blocklist.pack(side='left', padx=(10, 0))

        frame_path = ttk.Frame(root, padding=(10, 0, 10, 5))
        frame_path.pack(fill='x')
        ttk.Label(frame_path, text="所选路径:").pack(side='left')
        self.path_var = tk.StringVar()
        
        # 【新】v8.1 设置上次扫描的路径
        self.path_var.set(self.config.get('Settings', 'last_scan_path', fallback=''))
        
        self.entry_path = ttk.Entry(frame_path, textvariable=self.path_var, state='readonly')
        self.entry_path.pack(side='left', fill='x', expand=True, padx=(5, 0))

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
        self.tree.bind('<<TreeviewSelect>>', self.on_program_select)

        frame_actions = ttk.Frame(root, padding=10)
        frame_actions.pack(fill='x')
        self.btn_refine = ttk.Button(frame_actions, text="2. 详情/修改选择...", command=self.open_refine_window, state='disabled')
        self.btn_refine.pack(side='left')

        frame_bottom = ttk.Frame(root, padding=10)
        frame_bottom.pack(fill='x')
        self.btn_create = ttk.Button(frame_bottom, text="3. 生成所有快捷方式", command=self.generate_shortcuts, state='disabled')
        self.btn_create.pack(fill='x', ipady=4)

        frame_log = ttk.Frame(root, padding=(10, 5, 10, 5))
        frame_log.pack(fill='x')
        ttk.Label(frame_log, text="--- 日志输出 ---").pack()
        self.log_area = scrolledtext.ScrolledText(root, height=10, wrap=tk.WORD, state='disabled')
        self.log_area.pack(fill='x', expand=True, padx=10, pady=(0, 5))
        
        self.log(f"程序已启动。{msg}")
        self.log("请选择一个目录进行“程序发现”。")
        
        # 【新】v8.1 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def log(self, message):
        """(UI功能) 向日志区域追加一条消息"""
        self.log_area.config(state='normal')
        self.log_area.insert(tk.END, f"{message}\n")
        self.log_area.see(tk.END)
        self.log_area.config(state='disabled')
        self.root.update_idletasks() 

    def show_blocklist(self):
        """(UI功能) 管理黑名单的弹窗"""
        popup = tk.Toplevel(self.root)
        popup.title("管理黑名单")
        popup.geometry("400x300")
        popup.transient(self.root)
        popup.grab_set()

        lbl = ttk.Label(popup, text="每行一个文件名 (不区分大小写):", padding=10)
        lbl.pack()
        
        text_area = scrolledtext.ScrolledText(popup, height=10, wrap=tk.WORD, state='normal')
        text_area.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # 【新】v8.1 从内存加载黑名单
        for item in sorted(self.blocklist):
            text_area.insert(tk.END, f"{item}\n")
        
        frame_btns = ttk.Frame(popup, padding=10)
        frame_btns.pack(fill='x')

        def on_save():
            new_list = set(text_area.get(1.0, tk.END).split('\n'))
            self.blocklist = {item.lower() for item in new_list if item.strip()}
            
            # 【新】v8.1 调用后端保存
            success, msg = backend.save_blocklist(self.blocklist)
            if success:
                self.log(f"[+] 黑名单已保存。")
                popup.destroy()
            else:
                # 【新】v8.1 UI 负责显示错误
                messagebox.showerror("保存失败", msg, parent=popup)
        
        btn_save = ttk.Button(frame_btns, text="保存并关闭", command=on_save)
        btn_save.pack(side='right')
        btn_cancel = ttk.Button(popup, text="取消", command=popup.destroy)
        btn_cancel.pack(side='right', padx=10)

    def ask_scan_path(self):
        """(UI功能) 扫描按钮点击事件"""
        # 【新】v8.1 从配置加载初始目录
        initial_dir = self.config.get('Settings', 'last_scan_path', fallback=None)
        path_to_scan = filedialog.askdirectory(initialdir=initial_dir)
        
        if not path_to_scan:
            self.log("[提示] 用户取消了目录选择。")
            return 
            
        self.path_var.set(path_to_scan)
        
        # 【新】v8.1 调用后端扫描
        # 将 UI 的 self.log 方法作为回调传递给后端
        self.programs = backend.discover_programs(path_to_scan, self.blocklist, self.log)
        
        self.populate_main_treeview()
        self.btn_create.config(state='normal' if self.programs else 'disabled')

    def populate_main_treeview(self):
        """(UI功能) 填充主列表"""
        self.tree.delete(*self.tree.get_children())
        for i, prog_data in enumerate(self.programs):
            iid = str(i) 
            status_text = self.get_program_status_text(prog_data)
            self.tree.insert('', 'end', iid=iid, values=(prog_data['name'], status_text, prog_data['root_path']))

    def get_program_status_text(self, prog_data):
        count = len(prog_data['selected_exes'])
        if count == 0:
            return "(未选择)"
        elif count == 1:
            return os.path.basename(prog_data['selected_exes'][0])
        else:
            return f"({count} 个文件已选)"

    def on_program_select(self, event):
        if self.tree.selection():
            self.btn_refine.config(state='normal')
        else:
            self.btn_refine.config(state='disabled')

    def open_refine_window(self):
        selected_item_id = self.tree.selection()
        if not selected_item_id:
            return
        program_index = int(selected_item_id[0])
        program_data = self.programs[program_index]
        self.log(f"--- 打开详情: {program_data['name']} ---")
        
        refine_win = RefineWindow(self.root, program_data)
        self.root.wait_window(refine_win)
        
        self.log("--- 详情窗口已关闭 ---")
        status_text = self.get_program_status_text(program_data)
        self.tree.item(selected_item_id[0], values=(program_data['name'], status_text, program_data['root_path']))

    def generate_shortcuts(self):
        """(UI功能) 生成按钮点击事件"""
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        shortcut_dir = os.path.join(desktop_path, backend.OUTPUT_FOLDER_NAME)
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
                # 【新】v8.1 调用后端创建
                success, msg = backend.create_shortcut(full_path, os.path.join(shortcut_dir, f"{os.path.splitext(os.path.basename(full_path))[0]}.lnk"))
                
                self.log(f"    {msg}")
                if success:
                    total_created += 1
                else:
                    total_failed += 1
        
        self.log("--- 全部处理完成 ---")
        messagebox.showinfo("操作完成", 
                            f"操作已在桌面 '{backend.OUTPUT_FOLDER_NAME}' 文件夹中完成。\n\n"
                            f"成功: {total_created} 个\n"
                            f"失败: {total_failed} 个\n\n"
                            "详细日志请查看主窗口。")

    def on_closing(self):
        """(UI功能) 【新】v8.1 保存配置后退出"""
        self.log("正在保存配置...")
        self.config['Settings']['last_scan_path'] = self.path_var.get()
        self.config['Settings']['window_geometry'] = self.root.geometry()
        backend.save_config(self.config)
        self.root.destroy()

# --- 启动主程序 ---
if __name__ == "__main__":
    if os.name != 'nt':
        print("错误：此脚本需要 Windows (pywin32) 和 Tkinter 环境。")
    else:
        main_window = tk.Tk()
        app = App(main_window)
        main_window.mainloop()