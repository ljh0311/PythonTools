"""Fetch and cache GetGo fleet models from home.getgo.sg (public fleet pages)."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

FLEET_INDEX_URL = "https://home.getgo.sg/meet-the-fleet/"
FLEET_SEED_URL = "https://home.getgo.sg/meet-the-fleet/mg-4-2/"
# www.getgo.sg often scrapes cleanly when home.getgo.sg returns Cloudflare 1014
FLEET_ALT_URLS = [
    FLEET_SEED_URL,
    "https://www.getgo.sg/vehicles",
]
DEFAULT_REFRESH_HOURS = 24 * 30  # 1 month

_BLOCK_RE = re.compile(
    r"meet-the-fleet/([a-z0-9-]+)/[\s\S]*?\n([a-z ]+ electric|[a-z]+)\s*\n###\s+([^\n<]+)\s*\n([^\n<]+)\s*(?:\n(\d+\s+Seater))?",
    re.IGNORECASE,
)
_SLUG_RE = re.compile(r"/meet-the-fleet/([a-z0-9-]+)/", re.IGNORECASE)
_NAME_RE = re.compile(r"###\s+([A-Za-z0-9][^\n<]{2,80})")


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def cache_path(custom: Optional[Path] = None) -> Path:
    return custom or (_repo_root() / "getgo_fleet_cache.json")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slug_to_title(slug: str) -> str:
    parts = slug.replace("-", " ").split()
    out = []
    for p in parts:
        if p.lower() in ("ev", "cn7", "3rd", "4th", "2nd", "11th"):
            out.append(p.upper() if p.lower() == "ev" else p)
        elif p.isdigit():
            out.append(p)
        else:
            out.append(p.capitalize())
    return " ".join(out)


def parse_fleet_html(html: str, source_url: str = FLEET_SEED_URL) -> list[dict[str, Any]]:
    """Extract unique fleet models from GetGo fleet page HTML/markdown."""
    if not html or "Meet the fleet" not in html and "meet-the-fleet" not in html:
        return []

    models: list[dict[str, Any]] = []
    seen: set[str] = set()

    for slug, tier, name, vehicle_type, seats in _BLOCK_RE.findall(html):
        name = re.sub(r"\s+", " ", name.strip())
        if len(name) < 3:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        models.append(
            {
                "slug": slug.strip().lower(),
                "name": name,
                "tier": tier.strip().lower(),
                "vehicle_type": vehicle_type.strip(),
                "seats": (seats or "").strip(),
                "is_ev": "electric" in tier.lower() or " ev" in name.lower(),
            }
        )

    if not models:
        slugs = sorted(set(_SLUG_RE.findall(html)))
        for slug in slugs:
            if slug in ("meet-the-fleet",):
                continue
            name = slug_to_title(slug)
            key = name.casefold()
            if key in seen:
                continue
            seen.add(key)
            models.append(
                {
                    "slug": slug,
                    "name": name,
                    "tier": "",
                    "vehicle_type": "",
                    "seats": "",
                    "is_ev": "ev" in slug or "ioniq" in slug or slug.startswith("byd-"),
                }
            )

    models.sort(key=lambda m: m["name"].casefold())
    return models


def load_fleet_cache(path: Optional[Path] = None) -> dict[str, Any]:
    file_path = cache_path(path)
    if not file_path.exists():
        return {"models": [], "fetched_at": None, "source": FLEET_INDEX_URL}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        data.setdefault("models", [])
        return data
    except (OSError, json.JSONDecodeError):
        return {"models": [], "fetched_at": None, "source": FLEET_INDEX_URL}


def save_fleet_cache(data: dict[str, Any], path: Optional[Path] = None) -> Path:
    file_path = cache_path(path)
    payload = {
        "source": data.get("source", FLEET_INDEX_URL),
        "fetched_at": data.get("fetched_at") or _utc_now_iso(),
        "fetch_method": data.get("fetch_method", "cache"),
        "model_count": len(data.get("models", [])),
        "models": data.get("models", []),
    }
    file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return file_path


def is_cache_stale(
    cache: dict[str, Any], max_age_hours: float = DEFAULT_REFRESH_HOURS
) -> bool:
    fetched = cache.get("fetched_at")
    if not fetched or not cache.get("models"):
        return True
    try:
        ts = datetime.fromisoformat(str(fetched).replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age_h = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        return age_h >= max_age_hours
    except (TypeError, ValueError):
        return True


def model_names(cache: Optional[dict[str, Any]] = None, ev_only: bool = False) -> list[str]:
    data = cache or load_fleet_cache()
    names = []
    for m in data.get("models", []):
        if ev_only and not m.get("is_ev"):
            continue
        if not ev_only and m.get("is_ev") and "Getgo(EV)" not in str(m.get("tier", "")):
            pass
        name = m.get("name")
        if name:
            names.append(str(name))
    return sorted(set(names), key=str.casefold)


def _fetch_via_requests(url: str) -> tuple[Optional[str], str]:
    try:
        resp = requests.get(
            url,
            timeout=25,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CarRS-FleetSync/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if resp.status_code == 200 and "meet-the-fleet" in resp.text:
            return resp.text, "requests"
        return None, f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return None, str(exc)


def _fetch_via_firecrawl(url: str) -> tuple[Optional[str], str]:
    if not shutil.which("firecrawl"):
        return None, "firecrawl CLI not installed"
    with tempfile.TemporaryDirectory() as tmp:
        out_file = os.path.join(tmp, "fleet.md")
        try:
            proc = subprocess.run(
                ["firecrawl", "scrape", url, "-o", out_file],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode != 0:
                return None, (proc.stderr or proc.stdout or "firecrawl failed").strip()
            if os.path.exists(out_file):
                content = Path(out_file).read_text(encoding="utf-8", errors="replace")
                if content and "Error1014" not in content and "meet-the-fleet" in content:
                    return content, "firecrawl"
                return None, "firecrawl returned blocked or empty page"
        except (subprocess.TimeoutExpired, OSError) as exc:
            return None, str(exc)
    return None, "firecrawl failed"


def fetch_getgo_fleet(url: str = FLEET_SEED_URL) -> tuple[list[dict[str, Any]], str, str]:
    """
    Try fetchers in order. Returns (models, method, error_note).
    """
    errors = []
    urls = [url] + [u for u in FLEET_ALT_URLS if u != url]
    for try_url in urls:
        for method_name, fetcher in (
            ("firecrawl", lambda u=try_url: _fetch_via_firecrawl(u)),
            ("requests", lambda u=try_url: _fetch_via_requests(u)),
        ):
            html, note = fetcher()
            if html:
                models = parse_fleet_html(html, source_url=try_url)
                if models:
                    return models, method_name, ""
            errors.append(f"{try_url} {method_name}: {note}")

    return [], "none", "; ".join(errors)


def sync_getgo_fleet(
    force: bool = False,
    max_age_hours: float = DEFAULT_REFRESH_HOURS,
    path: Optional[Path] = None,
) -> dict[str, Any]:
    """
    Refresh fleet cache if stale or forced.
    Returns status dict for UI/logging.
    """
    cache = load_fleet_cache(path)
    if not force and not is_cache_stale(cache, max_age_hours):
        return {
            "ok": True,
            "updated": False,
            "message": "Fleet catalog is up to date",
            "model_count": len(cache.get("models", [])),
            "fetched_at": cache.get("fetched_at"),
            "fetch_method": cache.get("fetch_method", "cache"),
        }

    models, method, err = fetch_getgo_fleet()
    if models:
        payload = {
            "source": FLEET_SEED_URL,
            "fetched_at": _utc_now_iso(),
            "fetch_method": method,
            "models": models,
        }
        save_fleet_cache(payload, path)
        return {
            "ok": True,
            "updated": True,
            "message": f"Updated {len(models)} GetGo models via {method}",
            "model_count": len(models),
            "fetched_at": payload["fetched_at"],
            "fetch_method": method,
        }

    if cache.get("models"):
        return {
            "ok": True,
            "updated": False,
            "message": f"Fetch failed ({err}). Using cached {len(cache['models'])} models.",
            "model_count": len(cache.get("models", [])),
            "fetched_at": cache.get("fetched_at"),
            "fetch_method": cache.get("fetch_method", "cache"),
            "error": err,
        }

    return {
        "ok": False,
        "updated": False,
        "message": f"Could not fetch GetGo fleet: {err}",
        "model_count": 0,
        "error": err,
    }


def get_models_for_provider(provider: str, cache: Optional[dict[str, Any]] = None) -> list[str]:
    """Return combobox values for GetGo providers."""
    if provider not in ("Getgo", "Getgo(EV)"):
        return []
    data = cache or load_fleet_cache()
    if provider == "Getgo(EV)":
        return model_names(data, ev_only=True)
    return model_names(data, ev_only=False)
