# GGDesk

GGDesk 是一个面向 Windows 的桌面快捷方式扫描、分类和启动工具。仓库当前同时保留旧版 Python 代码和正在迁移的 Go/Wails 客户端；新功能优先进入 `go-client/`，`legacy/` 只用于迁移参考。

## 当前实现

Go/Wails 客户端已经支持：

- 读取或初始化本地 SQLite 快捷方式数据库
- 扫描开始菜单、UWP 和自定义目录中的程序
- 搜索、分类、重命名/删除分类和快捷方式归类
- 规则驱动的黑名单、忽略目录、扩展名和大小过滤
- 本地智能分类建议

仍在迁移或依赖 Windows 原生环境的能力包括图标提取、`.lnk` 深度解析、全局热键和长任务进度。旧 Python/Qt 实现不会被当作 Go 客户端的已完成能力。

## 架构

```text
go-client/
├── Go/Wails 后端、SQLite 访问和扫描逻辑
├── frontend/             Vite 前端
└── build/                Wails 构建配置与平台资源
legacy/                   Python/Qt 旧实现，仅作迁移参考
config/                   扫描规则和默认配置
data/                     本地运行时数据库（不应提交）
```

## 开发与验证

需要 Go 1.25+、Node.js 22+；完整桌面构建还需要 Wails CLI 和 Windows 环境。

```bash
cd go-client
npm ci --prefix frontend
npm run build --prefix frontend
go test ./...
```

`go test` 验证配置解析、目标规范化和扫描辅助逻辑；GitHub Actions 会在 Linux 上执行前端构建与 Go 测试。Linux/macOS 环境不能替代 Windows 真机的 Wails、Shell/COM 和快捷方式验收。

## 数据与隐私

`data/` 下的 SQLite 数据库、WAL/SHM 文件和运行日志属于本地状态，已加入 `.gitignore`。不要提交包含个人程序路径、快捷方式目标或其他本地环境信息的数据库；发布前请检查 `git diff --cached`。

## 文档

- [项目结构](README/ProjectStructure.md)
- [路线图](README/Roadmap.md)
- [更新记录](README/UpdateLog.md)
- [Go 客户端说明](go-client/README.md)

## 许可证

仓库当前没有根目录 `LICENSE` 文件。除非另行补充许可，不应把本项目作为已授权的开源组件再分发。

<!-- repo-readme-standard:v1 -->
## 仓库维护信息

- 项目类型：Windows 桌面工具
- 当前状态：Go/Wails 迁移中
- 可见性：public
- 维护节奏：按月验证 Go 客户端、前端构建和 Windows 专项能力
- 相关仓库：未发现功能相同、可直接合并的仓库
- 维护边界：归档、删除、历史重写或强制推送需单独确认
