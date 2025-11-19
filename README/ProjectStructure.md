
```text
GGDesk/
├── main.py                         # 🚀 程序启动入口 (Entry Point)
├── scanner_styles.py               # 🎨 UI 样式表定义 (QSS Theme Definitions)
│
├── config.ini                      # [自动生成] 用户配置文件 (User Configuration)
├── blocklist.txt                   # [自动生成] 文件名黑名单 (Filename Blacklist)
├── ignored_dirs.txt                # [自动生成] 目录黑洞列表 (Ignored Directories)
│
├── scanner_backend/                # 🧱 后端核心包 (Core Logic Package)
│   ├── __init__.py                 # 接口封装 (Facade): 对外暴露统一调用接口
│   ├── const.py                    # 常量定义: 默认配置、文件名常量
│   ├── core_discovery.py           # 核心算法: 递归扫描、分词评分 (Smart Rank)、去重逻辑
│   ├── manager_config.py           # 配置管理: INI 文件的读取与写入
│   ├── manager_rules.py            # 规则管理: TXT 规则文件的加载与保存
│   └── utils_system.py             # 系统工具: Windows API 调用 (快捷方式创建、UWP支持)
│
└── ui/                             # 🖥️ 前端界面包 (UI Package)
    ├── __init__.py                 # 包标识
    ├── main_window.py              # 主窗口: 侧边栏布局、页面堆栈调度、关于弹窗
    ├── page_scan.py                # [核心页面] 扫描程序: 多源扫描控制、结果列表、详情修改弹窗
    ├── page_rules.py               # [管理页面] 规则管理: 过滤策略、文件类型开关、黑名单编辑器
    ├── page_output.py              # [管理页面] 生成路径: 输出目录选择、现有快捷方式预览
    └── page_settings.py            # [设置页面] 系统设置: 主题切换、运行日志显示
```

-----

### 🧩 模块职责说明

#### **Backend (`scanner_backend/`)**

后端模块不包含任何 UI 代码，专注于数据处理和系统交互，便于未来移植或测试。

| 文件名 | 职责描述 |
| :--- | :--- |
| **`core_discovery.py`** | **大脑**。包含 `discover_programs`（扫描主逻辑）和 `smart_rank_executables`（智能评分算法）。负责从文件系统中提取数据并清洗。 |
| **`utils_system.py`** | **手脚**。负责底层操作，如创建 `.lnk` 快捷方式、解析 UWP `shell:AppsFolder`、调用资源管理器打开文件夹。 |
| **`manager_config.py`** | **记忆**。负责 `config.ini` 的序列化与反序列化，确保用户设置（如窗口大小、上次路径）持久化。 |
| **`manager_rules.py`** | **守卫**。负责读取和保存 `blocklist.txt` (黑名单) 和 `ignored_dirs.txt` (黑洞目录)。 |

#### **Frontend (`ui/`)**

前端模块负责界面渲染和用户交互，通过 `ScanWorker` 线程调用后端，防止界面卡死。

| 文件名 | 职责描述 |
| :--- | :--- |
| **`main_window.py`** | **骨架**。构建 Sidebar + StackedWidget 的主布局，处理全局信号（如状态栏更新、路径同步）。 |
| **`page_scan.py`** | **交互核心**。包含扫描线程 (`QThread`)、结果展示树 (`QTreeWidget`) 和详情修改弹窗 (`RefineWindow`)。 |
| **`page_rules.py`** | **控制台**。提供可视化的规则配置界面，支持文件类型勾选、大小阈值设定和规则列表编辑。 |
| **`page_output.py`** | **预览器**。管理生成的快捷方式存放位置，并实时预览该目录下已存在的文件。 |