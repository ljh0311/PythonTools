"""Shared surveillance UI palette — keep in sync with web_version/frontend/src/designTokens.js"""

SURVEILLANCE_COLORS = {
    "dark": {
        "bg": "#0d1117",
        "paper": "#161b22",
        "elevated": "#1c2128",
        "fg": "#e6edf3",
        "fg_muted": "#8b949e",
        "accent": "#4fc3f7",
        "secondary": "#81c784",
        "warning": "#d29922",
        "error": "#f85149",
        "success": "#3fb950",
        "status_bar": "#12161c",
        "border": "#30363d",
        "tooltip_bg": "#1c2128",
        "tooltip_fg": "#e6edf3",
    },
    "light": {
        "bg": "#f6f8fa",
        "paper": "#ffffff",
        "elevated": "#f0f3f6",
        "fg": "#1f2328",
        "fg_muted": "#656d76",
        "accent": "#0969da",
        "secondary": "#1a7f37",
        "warning": "#9a6700",
        "error": "#cf222e",
        "success": "#1a7f37",
        "status_bar": "#eaeef2",
        "border": "#d0d7de",
        "tooltip_bg": "#ffffff",
        "tooltip_fg": "#1f2328",
    },
}


def palette_for_mode(dark_mode: bool) -> dict:
    return SURVEILLANCE_COLORS["dark" if dark_mode else "light"]


def ui_colors_from_palette(palette: dict) -> dict:
    return {
        "bg": palette["bg"],
        "fg": palette["fg"],
        "fg_muted": palette["fg_muted"],
        "accent": palette["accent"],
        "highlight": palette["elevated"],
        "warning": palette["warning"],
        "error": palette["error"],
        "success": palette["success"],
        "paper": palette["paper"],
        "border": palette["border"],
        "tooltip_bg": palette["tooltip_bg"],
        "tooltip_fg": palette["tooltip_fg"],
        "status_bar": palette["status_bar"],
    }


def apply_ttk_styles(style, dark_mode: bool) -> dict:
    """Apply surveillance theme to a ttk.Style instance. Returns ui_colors dict."""
    palette = palette_for_mode(dark_mode)
    colors = ui_colors_from_palette(palette)
    bg = colors["bg"]
    fg = colors["fg"]
    paper = colors["paper"]
    accent = colors["accent"]
    border = colors["border"]
    fg_muted = colors["fg_muted"]

    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(".", background=bg, foreground=fg, font=("Segoe UI", 10))
    style.configure("TLabel", background=bg, foreground=fg)
    style.configure("TButton", padding=(10, 5))
    style.configure("TEntry", fieldbackground=paper, foreground=fg)
    style.configure("TCombobox", fieldbackground=paper, foreground=fg)
    style.configure("TFrame", background=bg)
    style.configure("Header.TFrame", background=palette["elevated"])
    style.configure("Toolbar.TFrame", background=paper)
    style.configure("TLabelframe", background=bg, foreground=fg, bordercolor=border)
    style.configure("TLabelframe.Label", background=bg, foreground=fg_muted, font=("Segoe UI", 9, "bold"))

    style.configure("Header.TLabel", font=("Segoe UI", 15, "bold"), foreground=fg, background=palette["elevated"])
    style.configure("HeaderSub.TLabel", font=("Segoe UI", 10), foreground=fg_muted, background=palette["elevated"])
    style.configure("SubHeader.TLabel", font=("Segoe UI", 12, "bold"), foreground=fg, background=bg)
    style.configure("Action.TButton", font=("Segoe UI", 10, "bold"))
    style.configure("Active.TLabel", foreground=colors["success"], background=bg)
    style.configure("Inactive.TLabel", foreground=colors["error"], background=bg)
    style.configure("Warning.TLabel", foreground=colors["warning"], background=bg)
    style.configure("Status.TLabel", font=("Segoe UI", 9), padding=6, background=colors["status_bar"], foreground=fg)

    style.configure("TNotebook", background=bg, borderwidth=0, tabmargins=(4, 4, 4, 0))
    style.configure(
        "TNotebook.Tab",
        padding=(16, 8),
        font=("Segoe UI", 10, "bold"),
        background=paper,
        foreground=fg_muted,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", accent), ("!selected", paper)],
        foreground=[("selected", bg if dark_mode else "#ffffff"), ("!selected", fg_muted)],
        expand=[("selected", [1, 1, 1, 0])],
    )

    style.map("TButton", background=[("active", palette["elevated"])])
    style.map("TCombobox", fieldbackground=[("readonly", paper)])

    return colors
