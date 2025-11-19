# 🚀 GGDesk

> **极简、智能的 Windows 桌面快捷方式启动与管理工具。** > *A Smart Desktop Shortcut Launcher & Manager.*

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![UI Framework](https://img.shields.io/badge/UI-PySide6-green.svg)](https://doc.qt.io/qtforpython/)
[![Status](https://img.shields.io/badge/Status-Beta%206.0-orange.svg)](./README/UpdateLog.md)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

---

## 📖 简介 (Introduction)

**GGDesk** 旨在解决 Windows 用户在管理大量免安装程序（Portable Apps）时遇到的痛点。它不再强迫用户手动创建每一个快捷方式，而是通过智能扫描和算法，一键生成并管理你的桌面入口。

### 🎯 解决痛点 (Pain Points Solved)
1.  **免安装程序的噩梦**：下载了许多绿色版软件，文件夹层级深，每次都要手动发送快捷方式到桌面？GGDesk 可以一键扫描并自动生成。
2.  **分类的繁琐性**：面对桌面上杂乱无章的图标感到头大？(🚧 *正在开发：借助 AI 自动化分类整理*)
3.  **识别困难**：一个目录下有 `app.exe`, `uninstall.exe`, `update.exe`，不知道点哪个？GGDesk 的智能评分算法帮你自动锁定主程序。

---

## ✨ 核心功能 (Features)

* **🔍 全能扫描**：支持扫描 **自定义文件夹**、**系统开始菜单** 以及 **Microsoft Store (UWP)** 应用。
* **🧠 智能评分算法**：基于分词匹配 (Token Matching) 和目录深度权重的算法，精准识别主程序 (如自动推荐 `idea64.exe` 而非 `launcher.exe`)。
* **🛡️ 规则引擎**：
    * **文件过滤**：支持黑名单、文件大小限制 (KB/MB)、扩展名筛选。
    * **黑洞目录**：自动跳过 `node_modules`, `.git` 等无关目录，极速扫描。
* **🎨 现代 UI**：基于 PySide6 的 Fluent 风格界面，支持 **暗黑/明亮** 主题切换。
* **🚦 智能查重**：生成前自动检测目标路径下已存在的快捷方式，避免重复和覆盖。

---

## 📚 文档导航 (Documentation)

为了保持根目录整洁，详细文档已归档至 `README/` 目录：

| 模块 | 说明 | 链接 |
| :--- | :--- | :--- |
| **🔮 未来规划** | 查看项目的后续开发计划、AI 集成路线图。 | [点击查看 Roadmap](./README/Roadmap.md) |
| **📝 更新记录** | 查看从 Alpha 到 Beta 版本的详细迭代日志。 | [点击查看 UpdateLog](./README/UpdateLog.md) |
| **📂 项目结构** | 了解前后端分离架构及各模块职责。 | [点击查看 ProjectStructure](./README/ProjectStructure.md) |

---

## 🛠️ 快速开始 (Quick Start)

### 环境要求
* Windows 10 / 11
* Python 3.11+

### 安装依赖
```bash
pip install PySide6 pywin32
````

### 运行程序

```bash
python main.py
```

-----

## 📂 项目结构简述

GGDesk 采用 **前后端分离** 与 **模块化** 的设计架构。

  * **前端 (Frontend)**：基于 `PySide6 (Qt)`，负责界面渲染与交互。
  * **后端 (Backend)**：纯 Python 逻辑，负责文件扫描、系统调用与配置管理。
  * **通信 (Communication)**：二者通过 Qt 的信号槽 (`Signal/Slot`) 机制解耦，确保界面流畅。

*(详细代码结构说明请查阅 [ProjectStructure](https://www.google.com/search?q=./README/ProjectStructure.md))*

-----

## 👨‍💻 关于作者

**By LceAn**

  * GitHub: [https://github.com/LceAn](https://github.com/LceAn)
  * Project: [https://github.com/LceAn/GGDesk](https://github.com/LceAn/GGDesk)

-----
