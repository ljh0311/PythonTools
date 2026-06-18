#!/data/data/com.termux/files/usr/bin/bash
# One-command CarRS install for Termux (no sed required).
# Run from the extracted folder:
#   cd ~/storage/downloads/CarRS-android-arm64 && bash android/go.sh

set -euo pipefail

ANDROID_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${ANDROID_DIR}/.." && pwd)"

fix_crlf() {
  local file="$1"
  local tmp="${file}.lf"
  tr -d '\r' < "${file}" > "${tmp}"
  mv "${tmp}" "${file}"
}

patch_legacy_installer() {
  local file="${ANDROID_DIR}/install.sh"
  local tmp="${file}.patched"
  local changed=0
  : > "${tmp}"
  while IFS= read -r line || [[ -n "${line}" ]]; do
    case "${line}" in
      *"pkg install -y python pip"*)
        line="${line/python pip/python}"
        changed=1
        ;;
    esac
    printf '%s\n' "${line}" >> "${tmp}"
  done < "${file}"
  if [[ "${changed}" -eq 1 ]]; then
    mv "${tmp}" "${file}"
    echo "Patched legacy install.sh (removed invalid pip package)."
  else
    rm -f "${tmp}"
  fi
}

cd "${ROOT}"

echo "=== CarRS bootstrap (Termux) ==="
fix_crlf "${ANDROID_DIR}/install.sh"
fix_crlf "${ANDROID_DIR}/carrs"
fix_crlf "${ANDROID_DIR}/verify_install.sh"
patch_legacy_installer

exec bash "${ANDROID_DIR}/install.sh"
