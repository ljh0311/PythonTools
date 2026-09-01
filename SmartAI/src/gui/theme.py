"""
Shared design tokens for the CustomTkinter robot control interface.
Keep colors and typography in one place for consistency with the web UI.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    """Semantic color and typography tokens (aligned with web CSS variables)."""

    # Brand
    PRIMARY = "#4285f4"
    PRIMARY_HOVER = "#3367d6"

    # Surfaces
    SURFACE = "#f8f9fa"
    SURFACE_ELEVATED = "#ffffff"
    BORDER = "#e5e7eb"
    STATUS_BAR_BG = "#f1f3f5"

    # Text
    TEXT = "#1f2937"
    TEXT_SECONDARY = "#6b7280"
    TEXT_ON_PRIMARY = "#ffffff"

    # Semantic status (WCAG-friendly, not neon)
    SUCCESS = "#16a34a"
    WARNING = "#d97706"
    DANGER = "#dc2626"
    DANGER_HOVER = "#b91c1c"
    INFO = "#2563eb"

    # Control sizing
    BTN_HEIGHT = 44
    BTN_MIN_WIDTH = 120
    EMERGENCY_HEIGHT = 52

    # Typography
    FONT_FAMILY = "Segoe UI"
    FONT_TITLE = (FONT_FAMILY, 18, "bold")
    FONT_SECTION = (FONT_FAMILY, 15, "bold")
    FONT_BODY = (FONT_FAMILY, 13)
    FONT_SMALL = (FONT_FAMILY, 11)
    FONT_BUTTON = (FONT_FAMILY, 13, "bold")
