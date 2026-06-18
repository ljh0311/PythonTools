#!/data/data/com.termux/files/usr/bin/bash
# Post-install smoke test for CarRS on Termux.
# Run after install.sh: bash android/verify_install.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${CARRS_HOME:-${HOME}/carrs}"
CARRS_BIN="${PREFIX}/bin/carrs"

fail=0

check() {
  if "$@"; then
    echo "OK: $*"
  else
    echo "FAIL: $*" >&2
    fail=1
  fi
}

echo "=== CarRS verify (Termux) ==="
echo "Arch: $(uname -m)"
echo "Python: $(python --version 2>&1)"
echo "Install dir: ${INSTALL_DIR}"
echo ""

if [[ ! -d "${INSTALL_DIR}" ]]; then
  echo "CarRS is not installed yet (missing ${INSTALL_DIR})." >&2
  echo "" >&2
  echo "From the extracted zip folder, run:" >&2
  echo "  cd ~/storage/downloads/CarRS-android-arm64" >&2
  echo "  sed -i 's/\\r$//' android/install.sh android/carrs android/verify_install.sh" >&2
  echo "  bash android/install.sh" >&2
  exit 1
fi

check test -f "${INSTALL_DIR}/run_recommendations.py"
check test -f "${INSTALL_DIR}/22 - Sheet1.csv"
if [[ -x "${CARRS_BIN}" ]] || command -v carrs >/dev/null 2>&1; then
  echo "OK: carrs command"
else
  echo "FAIL: carrs command not found (${CARRS_BIN})" >&2
  fail=1
fi

echo ""
echo "Syntax check..."
check python -m py_compile "${INSTALL_DIR}/run_recommendations.py"
check python -m py_compile "${INSTALL_DIR}/car_rental_recommender_core.py"

echo ""
echo "Dry-run recommendation (top 1)..."
run_carrs() {
  if command -v carrs >/dev/null 2>&1; then
    carrs "$@"
  elif [[ -x "${CARRS_BIN}" ]]; then
    "${CARRS_BIN}" "$@"
  else
    return 127
  fi
}

if run_carrs recommend --distance 10 --duration 2 --top 1 --no-ml; then
  echo "OK: recommend --no-ml"
else
  echo "Trying with ML enabled..."
  if run_carrs recommend --distance 10 --duration 2 --top 1; then
    echo "OK: recommend (with ML)"
  else
    echo "FAIL: recommend command" >&2
    fail=1
  fi
fi

echo ""
if [[ "${fail}" -eq 0 ]]; then
  echo "All checks passed."
else
  echo "Some checks failed." >&2
  exit 1
fi
