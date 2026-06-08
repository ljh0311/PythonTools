"""
Plug-and-play report coaching: optional Ollama (/api/generate), with rule-based fallback.

Environment (optional):
  TIMELOGGER_OLLAMA_URL   default http://localhost:11434/api/generate
  TIMELOGGER_OLLAMA_MODEL default llama3
"""

from __future__ import annotations

import os
from typing import Any, Mapping, MutableMapping, Sequence, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore


def _daily_tsv(rows: Sequence[Sequence[Any]], limit: int = 100) -> str:
    lines = ["date\thours\tearnings"]
    for r in rows[:limit]:
        try:
            lines.append(f"{r[0]}\t{float(r[1]):.2f}\t{float(r[2]):.2f}")
        except (TypeError, ValueError, IndexError):
            continue
    return "\n".join(lines)


def heuristic_insights(ctx: Mapping[str, Any]) -> str:
    wd = int(ctx.get("work_days") or 0)
    pd = int(ctx.get("period_days") or 1)
    ratio = wd / pd if pd else 0.0
    total_h = float(ctx.get("total_hours") or 0)
    avg_d = float(ctx.get("avg_daily_hours") or 0)
    proj = float(ctx.get("projected_total") or 0)
    earn = float(ctx.get("total_earnings_value") or 0)
    peak = str(ctx.get("peak_hours") or "N/A")

    lines = [
        "## Work habits (rule-based)",
        f"- You logged **{wd}** active days over **{pd}** calendar days (~{ratio:.0%} coverage).",
        f"- **Totals in range:** {total_h:.2f} h, **${earn:,.2f}** earnings.",
    ]
    if ratio < 0.25 and pd > 14:
        lines.append("- **Sparse logging** relative to the range — consider shorter report windows or more consistent entries for clearer trends.")
    elif ratio > 0.85 and pd >= 5:
        lines.append("- **High logging density** — good continuity for trend and projection signals.")

    if avg_d >= 9:
        lines.append("- **Long average days** — watch for burnout; consider shorter blocks or recovery days if this pace is sustained.")
    elif avg_d > 0 and avg_d <= 4 and wd >= 5:
        lines.append("- **Moderate daily hours** — if intentional (part-time), great; if not, check whether sessions are being split across days.")

    lines.extend(
        [
            f"- **Peak window** (from start/end times): {peak}.",
            f"- **Trends (from your stats panel):** hours {ctx.get('hours_trend', '—')}, earnings {ctx.get('earnings_trend', '—')}, rate {ctx.get('rate_trend', '—')}.",
            "",
            "## Planning & predictions (rule-based)",
            f"- Forward **30-day earnings projection** (model in app): **${proj:,.2f}** after the report end — use the Projection tab for weekday math.",
        ]
    )

    if wd > 0 and total_h > 0:
        target_week_h = min(total_h / wd * 5, total_h / wd * wd)
        lines.append(
            f"- **Next week rough hours target** (if you repeat recent intensity): ~**{target_week_h:.1f}** h/week "
            f"(based on {total_h:.1f} h over {wd} logged days, capped at 5-day pace)."
        )

    if ctx.get("compare_enabled"):
        lines.append(
            f"- **Period vs previous:** hours change {ctx.get('compare_hours', '—')}, earnings {ctx.get('compare_earnings', '—')} "
            f"(previous: {ctx.get('prev_hours', '—')} h, {ctx.get('prev_earnings', '—')})."
        )

    lines.append(
        "- **Tip:** For AI paragraphs, run [Ollama](https://ollama.com) locally and set `TIMELOGGER_OLLAMA_MODEL` to your installed model."
    )
    return "\n".join(lines)


def _ollama_generate(prompt: str, url: str, model: str, timeout: int) -> str | None:
    if not requests:
        return None
    payload = {"model": model, "prompt": prompt, "stream": False}
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict):
            if "response" in data and isinstance(data["response"], str):
                return data["response"].strip()
            msg = data.get("message")
            if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                return msg["content"].strip()
        return None
    except Exception:
        return None


def _build_llm_prompt(ctx: Mapping[str, Any]) -> str:
    detail = str(ctx.get("projection_detail") or "")
    if len(detail) > 3500:
        detail = detail[:3500] + "\n…(truncated)…"

    daily = _daily_tsv(ctx.get("daily_rows") or [], limit=80)

    te = float(ctx.get("total_earnings_value") or 0)
    ade = float(ctx.get("avg_daily_earnings_value") or 0)
    ar = float(ctx.get("avg_rate_value") or 0)

    header = f"""You are a concise productivity coach for an independent worker using a time/earnings log.

Report range: {ctx.get('from_date')} → {ctx.get('to_date')}
Summary:
- Total hours: {ctx.get('total_hours')}
- Total earnings: ${te:,.2f}
- Work days (days with logs): {ctx.get('work_days')} / period length {ctx.get('period_days')} days
- Avg hours per logged day: {ctx.get('avg_daily_hours')}
- Avg earnings per logged day: ${ade:,.2f}
- Avg hourly rate (aggregated): ${ar:,.2f}
- Most productive day: {ctx.get('most_productive')}
- Least productive day: {ctx.get('least_productive')}
- Peak hours (avg): {ctx.get('peak_hours')}
- Trends: hours {ctx.get('hours_trend')}; earnings {ctx.get('earnings_trend')}; rate {ctx.get('rate_trend')}; productivity {ctx.get('productivity_trend')}
- Compare previous period enabled: {ctx.get('compare_enabled')}
  Hours change: {ctx.get('compare_hours')}; earnings change: {ctx.get('compare_earnings')}
  Previous totals: {ctx.get('prev_hours')} h, {ctx.get('prev_earnings')}
- Model projection (30d after report end): ${float(ctx.get('projected_total') or 0):,.2f}

Daily sample (tab-separated):
{daily}

Projection / weekday model detail:
{detail}

Respond in **Markdown** with exactly two level-2 sections:
## Work habits
(4–6 bullets: strengths, risks, consistency, timing — grounded in numbers above.)

## Planning for the next 2 weeks
(4–6 bullets: concrete schedule/earnings goals; reference projection cautiously as an estimate; no legal/financial advice.)

Keep under 350 words. No preamble or closing pleasantries.
"""
    return header


def generate_insights(
    context: Mapping[str, Any],
    *,
    timeout: int = 90,
) -> Tuple[str, str]:
    """
    Returns (markdown_body, attribution_footer).

    Tries Ollama when `requests` is installed; otherwise or on failure, returns heuristic text.
    """
    url = os.environ.get("TIMELOGGER_OLLAMA_URL", "http://localhost:11434/api/generate")
    model = os.environ.get("TIMELOGGER_OLLAMA_MODEL", "llama3")

    base = heuristic_insights(context)
    if not requests:
        return base, "— Source: built-in rules (`pip install requests` + local Ollama for AI prose) —"

    prompt = _build_llm_prompt(context)
    llm = _ollama_generate(prompt, url, model, timeout=timeout)
    if llm:
        return llm, f"— Source: Ollama `{model}` @ {url} —"

    return base, "— Source: built-in rules (Ollama unavailable or returned no text) —"


def normalize_context(raw: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Fill defaults so callers may pass partial dicts during tests."""
    raw.setdefault("compare_enabled", False)
    raw.setdefault("daily_rows", [])
    return raw
