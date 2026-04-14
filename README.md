# MetaINFO Updater

Local Windows-first app to bulk write photo metadata (EXIF + IPTC + XMP) with a web UI and progress tracking.

## Features in this implementation
- Scan a folder for supported image files
- Apply global metadata to all scanned files
- Choose write mode per run:
  - `overwrite`: overwrite original files with automatic backup copy in `backend/data/backups`
  - `output_folder`: write updated copies to a separate output folder
- Live job progress via WebSocket
- Persisted job and file-level result tracking in SQLite

## Stack
- Backend: FastAPI + SQLite + ExifTool subprocess
- Frontend: React + Vite

## Supported formats
`.jpg`, `.jpeg`, `.png`, `.tif`, `.tiff`, `.webp`, `.heic`

## Prerequisites
- Python 3.11+
- Node.js 20+
- ExifTool installed and available on PATH (`exiftool` command)

## Run both backend + frontend in one command
From project root:

```bash
npm install
npm start
```

This starts both servers together:
- Frontend: `http://127.0.0.1:5173`
- Backend health: `http://127.0.0.1:8000/health`

Stop both with `Ctrl+C`.

## One-click in VS Code
This repo includes tasks in `.vscode/tasks.json`.

Use:
1. `Terminal` -> `Run Task...`
2. Select `Start Full System`

Optional tasks are also available:
- `Start Backend Only`
- `Start Frontend Only`

## macOS client delivery via GitHub Actions (DMG)
This repo includes a workflow at `.github/workflows/build-mac-dmg.yml`.

How to build a distributable DMG:
1. Push a tag like `v1.0.0`, or run the workflow manually from Actions (`workflow_dispatch`).
2. Download artifact: `TrackTECH-Meta-Updater-mac-dmg`.
3. Send `TrackTECH-Meta-Updater-mac.dmg` to your client.

### Optional: Apple code signing + notarization (recommended for clients)
Add these GitHub repository secrets before running the workflow:

- `APPLE_CERTIFICATE_P12`: base64-encoded Developer ID Application certificate (`.p12`)
- `APPLE_CERTIFICATE_PASSWORD`: password for that `.p12`
- `APPLE_SIGNING_IDENTITY`: exact codesign identity name, e.g. `Developer ID Application: Your Company (TEAMID)`
- `APPLE_ID`: Apple ID email used for notarization
- `APPLE_APP_SPECIFIC_PASSWORD`: app-specific password from Apple ID account
- `APPLE_TEAM_ID`: Apple Developer Team ID

When these secrets exist, the workflow will:
1. import cert into temporary keychain,
2. sign app bundles and DMG,
3. notarize DMG,
4. staple notarization ticket.

If secrets are missing, workflow still builds an unsigned DMG.

Inside the DMG:
- `TrackTECH Meta Updater.app` (start app)
- `TrackTECH Meta Updater Stop.app` (stop app)

Runtime behavior in packaged mac app:
- Tries preferred port `8000` first.
- If `8000` is busy, it automatically selects a free port.
- If an existing app instance is healthy, it reuses it and opens browser.
- Bundles ExifTool into the package build process.

## Manual run (separate terminals)
Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Run on macOS (one click)
Yes, macOS is supported.

1. Open Terminal in the project folder.
2. Run once to allow double-click launchers:

```bash
chmod +x run-mac.command stop-mac.command
```

3. Double-click `run-mac.command` in Finder to start backend + frontend and open the app.
4. Double-click `stop-mac.command` to stop both services.

If `exiftool` is missing on macOS:

```bash
brew install exiftool
```

## Notes
- For large folders, the scan preview returns only first 300 files in UI, but total count still includes all supported files.
- If ExifTool is missing, job processing will fail per file with clear errors until ExifTool is installed.
