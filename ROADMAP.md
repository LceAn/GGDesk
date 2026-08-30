# 未来更新计划（Roadmap）

> 最近更新：2026-08-30。项目处于 Python → Go/Wails 迁移期，新功能优先进入 `go-client/`。

## 短期（迁移收尾）

- 补齐仍在迁移中的能力：图标提取、`.lnk` 深度解析。
- 全局热键与长任务进度接入 Wails 事件机制。
- 迁移完成后将 `legacy/` 标记为冻结，README 移除对照性描述。

## 中期

- 发布 Windows 安装包（Wails build 产物 + 版本化 Release）。
- 快捷方式数据库的备份/恢复入口。
- 扫描规则的导入导出，便于多机同步分类偏好。

## 长期 / 想法

- 评估 macOS 支持的可行性（Wails 跨平台，但快捷方式/UWP 扫描需重写为 Finder/LaunchServices 逻辑）。
