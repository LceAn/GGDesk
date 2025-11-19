
### 📅 GGDesk Development Roadmap (Revised for Beta 5+)

#### 🟢 Phase 1: Foundation (基础架构与扫描) - [Released]
*已完成的核心功能模块。*

| Feature | Status | Version | Description |
| :--- | :--- | :--- | :--- |
| **Framework** | ✅ Done | Beta 1 | 迁移至 PySide6 (Qt)，确立模块化工程结构。 |
| **Smart Scan** | ✅ Done | Beta 5.1 | 多源扫描 (StartMenu/UWP/Custom) + 智能去重 + 评分算法。 |
| **Rule Engine** | ✅ Done | Beta 5.3 | 完善的过滤规则（黑名单/黑洞目录/大小/扩展名）与策略配置。 |
| **UX/UI** | ✅ Done | Beta 4.7 | Fluent 风格界面、侧边栏布局、交互式详情页、暗黑模式。 |
| **Conflict Check** | ✅ Done | Beta 4.4 | 生成前的路径冲突检测与覆盖保护。 |

#### 🟡 Phase 2: Data & Launcher (数据中心与启动器) - [Next Step: v1.0]
*构建核心数据库与主界面，实现“启动器”的本质功能。*

| Feature | Priority | Plan | Description |
| :--- | :--- | :--- | :--- |
| **Tiered DB** | 🔥 High | v0.9 | **数据库分级架构**：分离 `user_data.db` (核心) 与 `cache.db` (缓存)。实现 SQLite 基础增删改查封装。 |
| **Shadow Archive** | 🔥 High | v1.0 | **影子归档机制**：在生成快捷方式时，同步在程序目录下创建归档副本，确保数据安全。 |
| **Quick Launch** | 🔥 High | v1.0 | **首页重构**：新增“快捷启动”网格视图 (Grid View)，支持双击启动、右键菜单 (属性/定位)。 |
| **Launch Mgmt** | ⭐ Med | v1.0 | **启动管理页**：设置视图模式 (物理文件夹 vs 虚拟分类)、图标角标开关、排序方式 (按热度/名称)。 |
| **Data Care** | ⭐ Med | v1.0 | **数据维护中心**：提供核心数据备份/恢复功能；提供缓存文件大小查看与一键清理功能 (带二次确认)。 |
| **Update Check** | 🧊 Low | v1.0 | **版本检测**：启动时比对 GitHub Release 版本，在欢迎页展示更新公告与 Changelog。 |

#### 🔵 Phase 3: Advanced Interaction (高级交互与分类) - [v1.x]
*增强用户与程序的交互方式。*

| Feature | Priority | Plan | Description |
| :--- | :--- | :--- | :--- |
| **Hotkeys** | 🔥 High | v1.1 | 全局快捷键 (如 Alt+Space) 呼出/隐藏主窗口。 |
| **Smart Grouping** | ⭐ Med | v1.2 | **混合分类逻辑**：默认读取物理文件夹结构，同时支持用户创建虚拟标签进行多维度管理。 |
| **Visual Badges** | 🧊 Low | v1.2 | 动态绘制图标角标，直观展示程序来源 (Steam/UWP/Local)。 |
| **Usage Analytics** | 🧊 Low | v1.3 | 本地启动热度统计，生成“最常使用”排行榜。 |

#### 🟣 Phase 4: AI Intelligence (AI 赋能) - [v2.0]
*利用大模型能力提升自动化水平。*

| Feature | Priority | Plan | Description |
| :--- | :--- | :--- | :--- |
| **AI Core** | 🔥 High | v2.0 | **AI 模块集成**：接入 LLM API，建立提示词模板库 (`prompts.yaml`)。 |
| **Auto-Category** | ⭐ Med | v2.1 | **智能分类**：AI 分析程序名，自动归类 (开发/设计/游戏)，结果存入 `cache.db` 避免重复消耗 Token。 |
| **Smart Clean** | 🧊 Low | v2.2 | **智能清洗**：AI 辅助判断扫描结果中的“伪装”垃圾文件 (如卸载程序残留)。 |

#### 🔴 Phase 5: Desktop Revolution (桌面形态进化) - [Future]
*探索更激进的桌面交互形态。*

| Feature | Priority | Plan | Description |
| :--- | :--- | :--- | :--- |
| **Desktop Mode** | ❓ TBD | Future | **桌面格子 (Fences)**：嵌入桌面的分区收纳格，支持显示日历/天气。 |
| **Waterfall** | ❓ TBD | Future | **瀑布流 (Edge Bar)**：鼠标触碰屏幕边缘触发的侧边启动栏。 |

---
