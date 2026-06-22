# GGDeskGo

GGDeskGo is a parallel Go/Wails migration of the existing Python/Qt GGDesk app.

The Python version remains in the repository root. A working-tree snapshot was also created at:

```text
I:\github\GGDesk_python_snapshot_20260604_120740.zip
```

## Stack

- Go backend with Wails v2
- Vanilla Vite frontend
- SQLite storage using the existing `data/user_data.db`

## Current Scope

- Reads and initializes the current shortcut database.
- Lists shortcuts with search, category filter, and sorting.
- Launches shortcuts from the Go backend.
- Supports category create, rename, delete, and per-shortcut assignment.
- Provides local smart category suggestions.
- Provides a first-pass scanner for Start Menu `.lnk` files and custom-path `.exe` files.

## Local Toolchain

This machine did not have a system `go` command, so a portable Go SDK was installed under:

```text
C:\Users\LceAn\.cache\codex-runtimes\go-sdk\go1.26.4\go\bin\go.exe
```

Wails CLI was installed at:

```text
C:\Users\LceAn\go\bin\wails.exe
```

## Commands

From `go-client`:

```powershell
$env:PATH="$env:USERPROFILE\.cache\codex-runtimes\go-sdk\go1.26.4\go\bin;$env:USERPROFILE\go\bin;$env:PATH"
go test ./...
cd frontend
cmd /c npm run build
cd ..
wails build
```

The built app is:

```text
go-client\build\bin\go-client.exe
```

## Next Migration Steps

- Move icon extraction and caching into Go.
- Replace scan-time `.lnk` handling with native Windows Shell/COM resolution.
- Move long scans to cancellable background jobs with progress events.
- Port duplicate cleanup and path generation workflows.
- Add hotkey/global launcher behavior.
