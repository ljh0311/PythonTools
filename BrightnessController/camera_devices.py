"""Resolve Windows camera friendly names for OpenCV device indices."""

from __future__ import annotations

import subprocess
import sys
import winreg
from typing import List

VIDEO_INPUT_CLSID = r"{860BB310-5D01-11d0-BD3B-00A0C911CE86}"
DIRECTSHOW_INSTANCE_KEY = rf"SOFTWARE\Classes\CLSID\{VIDEO_INPUT_CLSID}\Instance"
DIRECTSHOW_INSTANCE_KEY_WOW64 = (
    rf"SOFTWARE\WOW6432Node\Classes\CLSID\{VIDEO_INPUT_CLSID}\Instance"
)


def _read_registry_friendly_names(root, path: str) -> List[str]:
    names: List[str] = []
    try:
        with winreg.OpenKey(root, path) as key:
            for i in range(winreg.QueryInfoKey(key)[0]):
                subkey_name = winreg.EnumKey(key, i)
                try:
                    with winreg.OpenKey(key, subkey_name) as subkey:
                        friendly, _ = winreg.QueryValueEx(subkey, "FriendlyName")
                        if friendly and friendly not in names:
                            names.append(str(friendly))
                except OSError:
                    continue
    except OSError:
        pass
    return names


def _directshow_registry_names() -> List[str]:
    names: List[str] = []
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for path in (DIRECTSHOW_INSTANCE_KEY, DIRECTSHOW_INSTANCE_KEY_WOW64):
            for name in _read_registry_friendly_names(root, path):
                if name not in names:
                    names.append(name)
    return names


def _pnp_camera_names() -> List[str]:
    if sys.platform != "win32":
        return []

    command = (
        "Get-PnpDevice -Class Camera -ErrorAction SilentlyContinue | "
        "Where-Object { $_.FriendlyName } | "
        "Select-Object -ExpandProperty FriendlyName"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return []

    names: List[str] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if name and name not in names:
            names.append(name)
    return names


def _wmi_camera_names() -> List[str]:
    try:
        import wmi  # type: ignore
    except ImportError:
        return []

    names: List[str] = []
    try:
        connection = wmi.WMI()
        for entity in connection.Win32_PnPEntity():
            pnp_class = (entity.PNPClass or "").strip()
            name = (entity.Name or "").strip()
            if not name:
                continue
            if pnp_class == "Camera" or (
                pnp_class == "Image" and "camera" in name.lower()
            ):
                if name not in names:
                    names.append(name)
    except Exception:
        return []

    return names


def enumerate_camera_names() -> List[str]:
    """
    Return camera friendly names in a stable order aligned with OpenCV CAP_DSHOW indices.

    PnP camera names are listed first, then DirectShow filter names not already seen.
    """
    merged: List[str] = []
    seen = set()

    for source in (_pnp_camera_names, _wmi_camera_names, _directshow_registry_names):
        for name in source():
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(name)

    return merged


def format_camera_label(index: int, name: str, all_names: List[str]) -> str:
    """Build a dropdown label; add index suffix only when names repeat."""
    duplicates = sum(1 for item in all_names if item.casefold() == name.casefold())
    if duplicates > 1:
        return f"{name} ({index})"
    return name


def get_camera_name(index: int, cached_names: List[str] | None = None) -> str:
    names = cached_names if cached_names is not None else enumerate_camera_names()
    if 0 <= index < len(names):
        return format_camera_label(index, names[index], names)
    return f"Camera {index}"
