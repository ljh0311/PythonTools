# CarRS on Samsung Galaxy S23 Ultra (Android)

**Target:** Samsung Galaxy S23 Ultra, Android 13+, **arm64-v8a** (aarch64)  
**Distribution:** Termux + headless CLI (`carrs` command)  
**Not supported on phone:** tkinter GUI (`car_rental_recommender_gui.py`), matplotlib charts, Ollama GUI dialogs

## Why Termux + CLI?

| Option | Verdict |
|--------|---------|
| **Termux + CLI** | Best fit: native arm64 Python, pip wheels, full terminal, minimal code changes |
| tkinter GUI | Not available on Android |
| BeeWare / Toga | Would require rewriting the entire GUI |
| Pydroid 3 | Possible but less reliable for scikit-learn; no shell automation |
| Docker on phone | Heavy; Termux is simpler for a personal CLI tool |

CarRS already ships a headless CLI (`run_recommendations.py`). The Android package wraps it as `carrs` for Termux.

---

## Prerequisites (on phone)

1. **Termux** from [F-Droid](https://f-droid.org/en/packages/com.termux/) (recommended) or [GitHub releases](https://github.com/termux/termux-app/releases) — avoid outdated Play Store builds.
2. Optional: **Termux:API** if you later automate file picks (not required for basic use).
3. Enable **Install unknown apps** only for F-Droid/GitHub APK sources you trust.

---

## Step 1 — Build release zip (on Windows PC)

From PowerShell in the CarRS folder:

```powershell
cd c:\Users\user\Documents\brightnessControl\PythonTools\CarRS
powershell -ExecutionPolicy Bypass -File android\package.ps1
```

Output: `CarRS\dist\CarRS-android-arm64.zip`

Alternative (Git Bash / WSL):

```bash
bash android/package.sh
```

---

## Step 2 — Transfer zip to S23 Ultra

Pick one method:

### USB cable

1. Connect phone to PC.
2. Copy `CarRS-android-arm64.zip` to **Internal storage → Download**.

### ADB (USB debugging enabled)

```powershell
adb devices
adb push "c:\Users\user\Documents\brightnessControl\PythonTools\CarRS\dist\CarRS-android-arm64.zip" /sdcard/Download/
```

### Cloud / messaging

Upload the zip and download it on the phone into **Download**.

---

## Step 3 — Install in Termux

1. Open **Termux**.
2. Grant storage (for CSV in Downloads):

   ```bash
   termux-setup-storage
   ```

   Allow the permission when Android prompts.

3. Extract and install (must run from inside the extracted folder):

   **Easiest — use the bootstrap (fixes CRLF + old zip scripts automatically):**

   ```bash
   cd ~/storage/downloads
   unzip -o CarRS-android-arm64.zip
   cd CarRS-android-arm64
   bash android/go.sh
   ```

   Or run the installer directly (new zip only):

   ```bash
   cd ~/storage/downloads/CarRS-android-arm64
   pkg install -y sed
   sed -i 's/\r$//' android/install.sh android/carrs android/verify_install.sh
   bash android/install.sh
   ```

   **Still on an old zip?** Patch in place, then install:

   ```bash
   cd ~/storage/downloads/CarRS-android-arm64
   pkg install -y sed
   sed -i 's/\r$//' android/install.sh android/carrs android/verify_install.sh
   sed -i 's/python pip/python/' android/install.sh
   bash android/install.sh
   ```

   You should see `=== CarRS Termux installer (v2) ===` — if not, the script is still outdated.

4. Verify:

   ```bash
   bash android/verify_install.sh
   ```

Install location: `~/carrs` (override with `CARRS_HOME` before running `install.sh`).

---

## Step 4 — Use CarRS on the phone

```bash
# Top recommendations for a 50 km, 3 h trip
carrs recommend --distance 50 --duration 3

# Malaysia providers, JSON for scripts
carrs recommend --distance 80 --duration 24 --region Malaysia --json

# Weekend pricing
carrs recommend --distance 50 --duration 3 --weekend

# Skip ML if scikit-learn failed to install
carrs recommend --distance 50 --duration 3 --no-ml

# List providers
carrs providers --region Singapore

# Clean a CSV
carrs clean "22 - Sheet1.csv" --out cleaned.csv

# Help
carrs help
```

### Use your own CSV

```bash
cp ~/storage/downloads/my-trips.csv ~/carrs/
carrs recommend --distance 60 --duration 4 --csv my-trips.csv
```

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `CARRS_HOME` | `~/carrs` | Installed app directory |
| `PYTHONPATH` | set by `carrs` | Ensures core module imports |

---

## Dependencies (Android)

File: `android/requirements-android.txt`

- pandas, numpy, tabulate, requests, scikit-learn  
- **Excluded:** matplotlib, tkinter (GUI-only)

If `scikit-learn` fails on Termux:

```bash
pkg install -y python-numpy python-scipy libopenblas liblapack
pip install --prefer-binary scikit-learn
```

Or use `--no-ml` until sklearn is fixed.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `$'/r': command not found` or `set: pipefail: invalid option` | Windows CRLF line endings. Run: `sed -i 's/\r$//' android/install.sh android/carrs android/verify_install.sh` then retry. Or: `tr -d '\r' < android/install.sh \| bash` |
| `unable to locate package pip` | Termux bundles pip with `python` (no separate pip package). Update scripts from latest zip, or run: `pkg install -y python && python -m pip install --upgrade pip` then re-run install |
| `carrs: command not found` | Restart Termux or `export PATH="$PREFIX/bin:$PATH"` |
| `CSV not found` | Use full path or copy CSV into `~/carrs` |
| `pip` / compile errors | Run `pkg upgrade`, then retry `install.sh` |
| ML errors | `carrs recommend ... --no-ml` |
| Permission denied on install.sh | `bash android/install.sh` (do not rely on `./` without chmod) |
| Wrong architecture | S23 Ultra must show `aarch64` in `uname -m` |

---

## Uninstall

```bash
rm -rf ~/carrs
rm -f $PREFIX/bin/carrs
pip uninstall -y pandas numpy tabulate requests scikit-learn
```

---

## Limitations

- **No GUI** on Android (tkinter unavailable).
- **No matplotlib** charts in CLI mode.
- **Ollama** integration is GUI-oriented; CLI uses historical + ML methods only.
- First `pip install` may take several minutes on mobile data.
- Windows/Docker workflows are unchanged; see [README.md](../README.md) and [docs/DOCKER.md](../docs/DOCKER.md).

---

## Files in this folder

| File | Purpose |
|------|---------|
| `requirements-android.txt` | arm64 CLI dependency pins |
| `install.sh` | Termux installer (idempotent) |
| `carrs` | Mobile CLI entry point |
| `verify_install.sh` | Post-install smoke test |
| `package.ps1` | Build zip on Windows |
| `package.sh` | Build zip on Unix/Git Bash |
| `INSTALL.md` | This document |
