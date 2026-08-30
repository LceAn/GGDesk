# 更新日志

本文件记录 GGDesk 的重要变更，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

## [未发布] - 2026-08-31

### 安全
- go-client Go 工具链从 1.25.0 升级到 1.25.13，规避标准库漏洞批次（GO-2026-6218/6091/6090/6089）。

## [未发布] - 2026-08-30

### 新增
- 新增 `CHANGELOG.md` 与 `ROADMAP.md`。
- README 增加文档索引。

### 说明
- 本次为文档整理，未改动 Go 客户端与 legacy 代码。

## 历史概要

- 2026-08-30 `test: stabilize Go client maintenance checks` — 稳定 Go 客户端维护性测试。
- 2026-07-28 `docs: standardize README structure` — 标准化 README，明确 `go-client/` 与 `legacy/` 的边界。
- 更早：Python/Qt 旧版桌面快捷方式启动工具（现保留于 `legacy/` 作迁移参考）。
