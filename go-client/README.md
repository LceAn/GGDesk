# GGDesk Go/Wails 客户端

这是 GGDesk 的 Go/Wails 迁移客户端，前端位于 `frontend/`，后端和 SQLite 数据访问位于当前目录。

## 本地命令

```bash
npm ci --prefix frontend
npm run build --prefix frontend
go test ./...
```

Wails 桌面打包仍需安装 Wails CLI，并在目标平台（尤其是 Windows）验证原生快捷方式、图标和窗口行为。`frontend/dist/.gitkeep` 只保证没有前端构建产物时 Go 包仍可测试；正式打包前必须先执行前端构建。

## 数据路径

程序从项目根目录的 `data/user_data.db` 读取本地状态，运行时 WAL/SHM 文件不会纳入版本控制。不要把个人快捷方式数据库复制到公开 issue 或构建日志。

## 迁移边界

当前优先维护 Go/Wails 客户端。`legacy/` 中的 Python/Qt 代码保留用于功能对照，尚未承诺与 Go 客户端行为完全一致。
