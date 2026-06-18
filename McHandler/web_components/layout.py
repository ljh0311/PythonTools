"""Register shared navbar/footer templates and static assets on a Flask app."""

from __future__ import annotations

import os
from typing import Any

from flask import Blueprint
from jinja2 import ChoiceLoader, FileSystemLoader

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))

layout_bp = Blueprint(
    'layout',
    __name__,
    static_folder='static',
    static_url_path='/web-components',
)

MINECRAFT_LAYOUT: dict[str, Any] = {
    'brand_icon': 'fa-cube',
    'brand_title': 'Minecraft Mod Handler',
    'nav_items': [
        {'endpoint': 'index', 'label': 'Dashboard', 'icon': 'fa-home'},
        {'endpoint': 'mods', 'label': 'Mods', 'icon': 'fa-puzzle-piece'},
        {'endpoint': 'shaders', 'label': 'Shaders', 'icon': 'fa-palette'},
        {'endpoint': 'crash_analysis', 'label': 'Crash Analysis', 'icon': 'fa-bug'},
        {'endpoint': 'compatibility', 'label': 'Compatibility', 'icon': 'fa-check-double'},
        {'endpoint': 'settings', 'label': 'Settings', 'icon': 'fa-cog'},
    ],
    'footer_year': 2024,
    'footer_copyright': 'Minecraft Mod Handler',
    'footer_tagline': None,
    'ollama_status_text': 'AI status on Dashboard',
    'ollama_status_font_size': '0.9rem',
    'ollama_status_icon_size': '0.8em',
}

CDID_LAYOUT: dict[str, Any] = {
    'brand_icon': 'fa-car',
    'brand_title': 'CDID Car Tuning Assistant',
    'nav_items': [
        {'endpoint': 'index', 'label': 'Home', 'icon': 'fa-home'},
        {'endpoint': 'help_page', 'label': 'Help', 'icon': 'fa-question-circle'},
    ],
    'footer_year': 2024,
    'footer_copyright': 'CDID Car Tuning Assistant',
    'footer_tagline': 'Roblox CDID',
    'ollama_status_text': 'Checking AI Engine...',
    'ollama_status_font_size': '1rem',
    'ollama_status_icon_size': '0.9em',
}

LAYOUT_PRESETS = {
    'minecraft': MINECRAFT_LAYOUT,
    'cdid': CDID_LAYOUT,
}


def register_layout(app, preset: str = 'minecraft', **overrides: Any) -> dict[str, Any]:
    """
    Wire shared navbar/footer into a Flask app.

    Usage:
        register_layout(app, 'minecraft')
        register_layout(app, 'cdid', footer_year=2025)
    """
    if preset not in LAYOUT_PRESETS:
        raise ValueError(f'Unknown layout preset {preset!r}; choose from {list(LAYOUT_PRESETS)}')

    config = {**LAYOUT_PRESETS[preset], **overrides}

    app.register_blueprint(layout_bp)

    shared_templates = os.path.join(_PKG_DIR, 'templates')
    app.jinja_loader = ChoiceLoader([
        app.jinja_loader,
        FileSystemLoader(shared_templates),
    ])

    @app.context_processor
    def _inject_layout() -> dict[str, Any]:
        return {'layout': config}

    return config
