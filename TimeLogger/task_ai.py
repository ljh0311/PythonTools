"""Optional Ollama task planning with predictable rule-based fallbacks.

Environment (optional):
  TIMELOGGER_OLLAMA_URL   default http://localhost:11434/api/generate
  TIMELOGGER_OLLAMA_MODEL default llama3
"""
from __future__ import annotations

import os
from typing import Any, Mapping, Sequence, Tuple

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore


def plan_tasks(context: Mapping[str, Any], *, timeout: int = 90) -> Tuple[str, str]:
    """Return a prioritized Markdown task plan and an Ollama/rules attribution."""
    fallback = _heuristic_plan(context)
    ai = _ask_ollama(_plan_prompt(context), timeout)
    if ai:
        return ai, _ollama_footer()
    return fallback, _fallback_footer()


def summarize_period(context: Mapping[str, Any], *, timeout: int = 90) -> Tuple[str, str]:
    """Return a Markdown summary of completed tasks and its attribution."""
    fallback = _heuristic_summary(context)
    ai = _ask_ollama(_summary_prompt(context), timeout)
    if ai:
        return ai, _ollama_footer()
    return fallback, _fallback_footer()


def _tasks(context: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = context.get("tasks") or []
    return [task for task in raw if isinstance(task, Mapping)]


def _heuristic_plan(context: Mapping[str, Any]) -> str:
    tasks = _tasks(context)
    if not tasks:
        return "## Task plan (rule-based)\n\n- No open tasks yet. Add a task to generate a plan."
    lines = ["## Task plan (rule-based)", ""]
    for index, task in enumerate(tasks[:8], 1):
        due = task.get("due_date") or "no due date"
        lines.append(
            f"{index}. **{task.get('title', 'Untitled')}** — {task.get('status', 'todo')}; "
            f"priority {task.get('priority', '?')}/15; due {due}."
        )
    lines.extend(["", "Start with the first item, work in a focused block, then update its status."])
    return "\n".join(lines)


def _heuristic_summary(context: Mapping[str, Any]) -> str:
    tasks = _tasks(context)
    label = context.get("period_label") or "Selected period"
    if not tasks:
        return f"## {label} completed tasks (rule-based)\n\n- No completed tasks in this period."
    total_priority = sum(int(task.get("priority") or 0) for task in tasks)
    titles = ", ".join(str(task.get("title") or "Untitled") for task in tasks[:8])
    return (
        f"## {label} completed tasks (rule-based)\n\n"
        f"- Completed **{len(tasks)}** task(s), totaling **{total_priority}** priority points.\n"
        f"- Finished: {titles}.\n"
        "- Review unfinished high-priority tasks before planning the next period."
    )


def _plan_prompt(context: Mapping[str, Any]) -> str:
    return (
        "You are a concise task planner. Prioritize the following open tasks. "
        "Return Markdown with a level-2 heading and 3-8 actionable bullets; mention due dates and "
        "do not invent facts.\n\nOpen tasks:\n" + _task_lines(_tasks(context))
    )


def _summary_prompt(context: Mapping[str, Any]) -> str:
    return (
        "You are a concise productivity coach. Summarize these completed tasks for "
        f"{context.get('period_label') or 'the selected period'}. Return Markdown with a level-2 heading "
        "and 2-5 factual bullets. Do not invent facts.\n\nCompleted tasks:\n" + _task_lines(_tasks(context))
    )


def _task_lines(tasks: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(
        f"- {task.get('title', 'Untitled')} | status={task.get('status')} | "
        f"priority={task.get('priority')} | due={task.get('due_date') or 'none'} | "
        f"completed={task.get('completed_date') or 'none'} | notes={task.get('notes') or ''}"
        for task in tasks[:30]
    ) or "- None"


def _ask_ollama(prompt: str, timeout: int) -> str | None:
    if not requests:
        return None
    url = os.environ.get("TIMELOGGER_OLLAMA_URL", "http://localhost:11434/api/generate")
    model = os.environ.get("TIMELOGGER_OLLAMA_MODEL", "llama3")
    try:
        response = requests.post(
            url, json={"model": model, "prompt": prompt, "stream": False}, timeout=timeout
        )
        response.raise_for_status()
        body = response.json()
        text = body.get("response") if isinstance(body, dict) else None
        return text.strip() if isinstance(text, str) and text.strip() else None
    except Exception:
        return None


def _ollama_footer() -> str:
    url = os.environ.get("TIMELOGGER_OLLAMA_URL", "http://localhost:11434/api/generate")
    model = os.environ.get("TIMELOGGER_OLLAMA_MODEL", "llama3")
    return f"— Source: Ollama `{model}` @ {url} —"


def _fallback_footer() -> str:
    return "— Source: built-in rules (Ollama unavailable or returned no text) —"
