#!/data/data/com.termux/files/usr/bin/bash
# Install CarRS on Termux (Samsung Galaxy S23 Ultra / Android arm64-v8a).
# Run from the extracted release folder:
#   cd ~/storage/downloads/CarRS-android-arm64 && bash android/install.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
INSTALL_DIR="${CARRS_HOME:-${HOME}/carrs}"
TERMUX_BIN="${PREFIX}/bin"
CARRS_BIN="${TERMUX_BIN}/carrs"
PIP="python -m pip"

REQUIRED_FILES=(
  car_rental_recommender_core.py
  run_recommendations.py
  run_cleaning_pipeline.py
  pricing_config.json
  settings.json
  "22 - Sheet1.csv"
)

echo "=== CarRS Termux installer (v2) ==="
echo "Source:  ${SOURCE_ROOT}"
echo "Install: ${INSTALL_DIR}"
echo "Arch:    $(uname -m) (expect aarch64 for S23 Ultra)"
echo ""

if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "Warning: expected aarch64 (arm64-v8a). Continuing anyway." >&2
fi

missing=0
for item in "${REQUIRED_FILES[@]}"; do
  if [[ ! -f "${SOURCE_ROOT}/${item}" ]]; then
    echo "Error: missing ${SOURCE_ROOT}/${item}" >&2
    missing=1
  fi
done
if [[ "${missing}" -ne 0 ]]; then
  echo "" >&2
  echo "Extract the zip, then run from inside CarRS-android-arm64:" >&2
  echo "  cd ~/storage/downloads/CarRS-android-arm64" >&2
  echo "  bash android/install.sh" >&2
  exit 1
fi

echo "[1/5] Updating Termux packages..."
pkg update -y
# pip is bundled with python in current Termux — there is no separate "pip" package.
pkg install -y python

echo "[2/5] Copying CarRS app files to ${INSTALL_DIR}..."
mkdir -p "${INSTALL_DIR}"
for item in "${REQUIRED_FILES[@]}"; do
  cp -f "${SOURCE_ROOT}/${item}" "${INSTALL_DIR}/"
done

echo "[3/5] Installing carrs command..."
mkdir -p "${TERMUX_BIN}"
cp -f "${SCRIPT_DIR}/carrs" "${CARRS_BIN}"
chmod +x "${CARRS_BIN}"
sed -i 's/\r$//' "${CARRS_BIN}" "${SCRIPT_DIR}/carrs" 2>/dev/null || true

echo "[4/5] Installing build helpers (for scikit-learn wheels/build)..."
pkg install -y libopenblas liblapack || true

echo "[5/5] Installing Python dependencies..."
cd "${INSTALL_DIR}"
python -m ensurepip --upgrade 2>/dev/null || true
${PIP} install --upgrade pip 2>/dev/null || true

if ! ${PIP} install -r "${SCRIPT_DIR}/requirements-android.txt"; then
  echo "pip install failed; trying Termux numpy/scipy packages then scikit-learn..." >&2
  pkg install -y python-numpy python-scipy || true
  ${PIP} install pandas tabulate requests "numpy>=1.24" || true
  ${PIP} install --prefer-binary scikit-learn || {
    echo "scikit-learn install failed. ML features disabled unless you fix this." >&2
    echo "You can still run: carrs recommend ... --no-ml" >&2
  }
fi

echo ""
echo "=== Install complete ==="
echo ""
echo "Installed to: ${INSTALL_DIR}"
echo "Command:      carrs"
echo ""
echo "Quick test:"
echo "  carrs recommend --distance 50 --duration 3 --top 3"
echo ""
echo "Verify:"
echo "  bash android/verify_install.sh"
echo ""
echo "If 'carrs' is not found, restart Termux or run:"
echo "  export PATH=\"${TERMUX_BIN}:\$PATH\""
