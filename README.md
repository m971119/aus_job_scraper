# Aus Job Scraper

Scrapes recent jobs from Seek.com.au and displays them in a web UI.

## Quick Start

Copy `.env.example` to `.env`, then:

```bash
./scripts/start.sh   # Mac/Linux
scripts\start.bat    # Windows
```

Open http://localhost:3000

## Debugging

To debug the backend with breakpoints in Cursor or VS Code:

1. Run `./scripts/debug.sh` — starts only the frontend Docker container
2. Open the Run & Debug panel (`Cmd+Shift+D`) and launch **Backend: FastAPI**
3. Open http://localhost:3000 — the frontend calls your local debug backend on port 8000

To stop: `./scripts/stop.sh`

## Scripts

| Script | Description |
|---|---|
| `scripts/start.sh` | Start all services via Docker Compose |
| `scripts/stop.sh` | Stop all services |
| `scripts/debug.sh` | Start frontend only (use debugger for backend) |
