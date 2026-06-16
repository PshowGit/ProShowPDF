# ProShow PDF v1.0.0 — Deployment Instructions

## Build Status

✅ **Executable built:** `dist\ProShowPDF\ProShowPDF.exe` (3.5 MB)
✅ **Distribution package:** `ProShowPDF-v1.0.0-windows-x64.zip` (312 MB)
✅ **Source:** https://github.com/PshowGit/ProShowPDF (master branch)

---

## How to Create GitHub Release (Manual)

### Option A: Via GitHub Web UI (Easiest)

1. Go to https://github.com/PshowGit/ProShowPDF/releases
2. Click **"Create a new release"** (or **"Draft a new release"**)
3. Fill in:
   - **Tag version:** `v1.0.0`
   - **Release title:** `ProShow PDF v1.0.0`
   - **Description:** (see below)
   - **Attach binaries:** Upload `ProShowPDF-v1.0.0-windows-x64.zip`
4. Click **"Publish release"**

### Option B: Via GitHub CLI (if installed)

```bash
cd D:\Programmi\ProShowPDF
gh release create v1.0.0 \
  --title "ProShow PDF v1.0.0" \
  --notes "Web-to-PDF converter for Windows x64. See README.md for features and usage." \
  ProShowPDF-v1.0.0-windows-x64.zip
```

### Option C: Via git + curl (requires GITHUB_TOKEN)

```bash
export GITHUB_TOKEN=<your-personal-access-token>
# Then run the commands from Option B
```

---

## Release Description Template

```
# ProShow PDF v1.0.0

**Web-to-PDF Converter for Windows x64**

Convert web pages to single-page continuous PDFs with high visual fidelity.

## Features

- **Modern GUI** — Dark/light theme, drag-and-drop URL input (txt/csv/xlsx)
- **Batch Processing** — Configurable concurrent conversions, real-time progress
- **Smart Rendering** — Dynamic page height, on-screen appearance, full lazy-load support
- **Cookie Consent** — Auto-dismiss common consent banners
- **Error Handling** — Per-URL error classification, CSV export
- **Settings Persistence** — Remember preferences across sessions

## System Requirements

- Windows 10/11 64-bit (x64)
- No installation needed — extract and run

## How to Use

1. Extract `ProShowPDF-v1.0.0-windows-x64.zip`
2. Run `ProShowPDF\ProShowPDF.exe`
3. Paste URLs or drag-and-drop txt/csv/xlsx files
4. Adjust settings (width, parallel jobs, timeout, retries, etc.)
5. Click "Converti" and wait for completion
6. PDFs saved to your chosen folder

## Documentation

- **README.md** — Setup and usage guide
- **CLAUDE.md** — Architecture and development guide
- **docs/superpowers/** — Detailed design spec and implementation plan

## What's Included

- **ProShowPDF.exe** (3.5 MB) — Main executable
- **ms-playwright/** — Bundled Chromium (Headless Shell + ffmpeg)
- **proshowpdf/resources/** — QSS themes and icons
- Everything needed to run, no additional installation required

## Known Limitations

- Pages with aggressive anti-bot detection may fail
- Cookie banners not 100% covered (can be disabled from UI)
- Very tall single-page PDFs can be large files

---

## Verification Checklist

Before releasing, verify:

- [ ] Executable runs without errors: `ProShowPDF.exe`
- [ ] Theme toggle works (light ↔ dark)
- [ ] Drag-and-drop URL input accepts txt/csv/xlsx files
- [ ] Conversions complete successfully (test with example.com)
- [ ] Progress bar and error handling work
- [ ] "Sfoglia" (output folder) button is visible and functional
- [ ] All settings persist across restarts

---

## Post-Release

Once released:

1. Announce on relevant channels (GitHub discussions, forums, etc.)
2. Monitor issues and bug reports
3. Plan maintenance releases (v1.0.1+) as needed

---

**Build Date:** 2026-06-16
**Git Commit:** (check latest via `git log --oneline | head -1`)
**Status:** Ready for production
