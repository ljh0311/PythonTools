#!/usr/bin/env bash
# Build CarRS-android-arm64 release zip on Linux/macOS/WSL/Git Bash.
# Output: ../dist/CarRS-android-arm64.zip

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${ROOT}/dist"
ZIP="${OUT_DIR}/CarRS-android-arm64.zip"
STAGE="${OUT_DIR}/CarRS-android-arm64"

rm -rf "${STAGE}"
mkdir -p "${STAGE}/android" "${OUT_DIR}"

copy_if_exists() {
  local src="${ROOT}/$1"
  local dest="${STAGE}/$1"
  if [[ -f "${src}" ]]; then
    mkdir -p "$(dirname "${dest}")"
    cp "${src}" "${dest}"
  else
    echo "Warning: missing ${src}" >&2
  fi
}

copy_if_exists "car_rental_recommender_core.py"
copy_if_exists "run_recommendations.py"
copy_if_exists "run_cleaning_pipeline.py"
copy_if_exists "pricing_config.json"
copy_if_exists "settings.json"
copy_if_exists "22 - Sheet1.csv"
cp "${ROOT}/android/"* "${STAGE}/android/"

chmod +x "${STAGE}/android/install.sh" "${STAGE}/android/carrs" 2>/dev/null || true

(
  cd "${OUT_DIR}"
  rm -f "$(basename "${ZIP}")"
  zip -r "$(basename "${ZIP}")" "$(basename "${STAGE}")"
)

echo "Created: ${ZIP}"
echo "Transfer to phone (ADB): adb push \"${ZIP}\" /sdcard/Download/"
