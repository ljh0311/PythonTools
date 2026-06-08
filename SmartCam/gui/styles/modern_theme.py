"""
Modern theme system for SmartCam GUI.
Provides centralized styling configuration with modern design principles.
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Tuple, Optional

# ============================================================================
# COLOR PALETTE
# ============================================================================

# Light Mode Colors
LIGHT_COLORS = {
    # Primary colors
    'primary': '#2563eb',           # Blue
    'primary_hover': '#1d4ed8',     # Darker blue
    'primary_light': '#dbeafe',     # Light blue background
    'secondary': '#64748b',         # Slate gray
    'secondary_hover': '#475569',   # Darker slate
    
    # Semantic colors
    'success': '#10b981',           # Green
    'success_light': '#d1fae5',     # Light green background
    'warning': '#f59e0b',           # Amber
    'warning_light': '#fef3c7',     # Light amber background
    'error': '#ef4444',             # Red
    'error_light': '#fee2e2',       # Light red background
    'info': '#3b82f6',              # Info blue
    'info_light': '#dbeafe',        # Light info background
    
    # Neutral colors
    'background': '#f8fafc',        # Very light gray
    'surface': '#ffffff',           # White
    'surface_elevated': '#ffffff',  # White with shadow
    'border': '#e2e8f0',            # Light border
    'border_light': '#f1f5f9',      # Very light border
    
    # Text colors
    'text_primary': '#0f172a',      # Almost black
    'text_secondary': '#475569',    # Medium gray
    'text_tertiary': '#94a3b8',     # Light gray
    'text_inverse': '#ffffff',      # White text
    
    # Special
    'preview_bg': '#000000',        # Black for camera preview
    'overlay': '#4a4a4a',           # Semi-transparent overlay (dark gray, approximates rgba(0,0,0,0.5))
}

# Dark Mode Colors (for future use)
DARK_COLORS = {
    'primary': '#3b82f6',
    'primary_hover': '#2563eb',
    'background': '#0f172a',
    'surface': '#1e293b',
    'text_primary': '#f1f5f9',
    'text_secondary': '#cbd5e1',
    # ... (can be expanded)
}

# Current theme (defaults to light)
CURRENT_THEME = LIGHT_COLORS

# ============================================================================
# SPACING SYSTEM (4px base unit)
# ============================================================================

SPACING = {
    'xs': 4,      # 4px
    'sm': 8,      # 8px
    'md': 12,     # 12px
    'lg': 16,     # 16px
    'xl': 24,     # 24px
    '2xl': 32,    # 32px
    '3xl': 48,    # 48px
}

# ============================================================================
# TYPOGRAPHY
# ============================================================================

FONTS = {
    'heading_large': ('Segoe UI', 24, 'bold'),
    'heading_medium': ('Segoe UI', 18, 'bold'),
    'heading_small': ('Segoe UI', 14, 'bold'),
    'body_large': ('Segoe UI', 12, 'normal'),
    'body': ('Segoe UI', 10, 'normal'),
    'caption': ('Segoe UI', 8, 'normal'),
    'monospace': ('Consolas', 10, 'normal'),
    'monospace_small': ('Consolas', 9, 'normal'),
}

# ============================================================================
# BORDER RADIUS
# ============================================================================

BORDER_RADIUS = {
    'sm': 4,
    'md': 6,
    'lg': 8,
    'xl': 12,
    'full': 9999,  # For circular elements
}

# ============================================================================
# SHADOWS (simulated with borders and colors)
# ============================================================================

SHADOWS = {
    'sm': {'relief': 'flat', 'borderwidth': 1, 'highlightthickness': 0},
    'md': {'relief': 'flat', 'borderwidth': 1, 'highlightthickness': 1},
    'lg': {'relief': 'flat', 'borderwidth': 2, 'highlightthickness': 1},
}

# ============================================================================
# THEME APPLICATION FUNCTIONS
# ============================================================================

def get_color(name: str) -> str:
    """Get a color from the current theme."""
    return CURRENT_THEME.get(name, '#000000')

def get_spacing(size: str) -> int:
    """Get spacing value."""
    return SPACING.get(size, 8)

def get_font(name: str) -> Tuple[str, int, str]:
    """Get font tuple."""
    return FONTS.get(name, FONTS['body'])

def apply_modern_theme(root: tk.Tk, style: Optional[ttk.Style] = None):
    """
    Apply modern theme to ttk widgets.
    
    Args:
        root: Root tkinter window
        style: Optional ttk.Style instance (creates one if not provided)
    """
    if style is None:
        style = ttk.Style()
    
    # Configure base styles
    style.theme_use('clam')  # Use clam as base for better customization
    
    # Configure colors
    style.configure('TFrame', 
                   background=get_color('background'),
                   borderwidth=0)
    
    style.configure('TLabel',
                   background=get_color('background'),
                   foreground=get_color('text_primary'),
                   font=get_font('body'))
    
    style.configure('TLabelFrame',
                   background=get_color('background'),
                   foreground=get_color('text_primary'),
                   borderwidth=1,
                   relief='flat')
    
    style.configure('TLabelFrame.Label',
                   background=get_color('background'),
                   foreground=get_color('text_primary'),
                   font=get_font('heading_small'))
    
    # Button styles
    style.configure('TButton',
                   background=get_color('primary'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0,
                   focuscolor='none',
                   padding=(SPACING['md'], SPACING['sm']),
                   font=get_font('body'))
    
    style.map('TButton',
             background=[('active', get_color('primary_hover')),
                        ('disabled', get_color('border')),
                        ('focus', get_color('primary_light'))],
             foreground=[('disabled', get_color('text_tertiary'))])
    
    # Action button style (larger, more prominent)
    style.configure('Action.TButton',
                   background=get_color('primary'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0,
                   padding=(SPACING['lg'], SPACING['md']),
                   font=get_font('body_large'))
    
    style.map('Action.TButton',
             background=[('active', get_color('primary_hover')),
                        ('focus', get_color('primary_light'))])
    
    # Secondary button style
    style.configure('Secondary.TButton',
                   background=get_color('secondary'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0,
                   padding=(SPACING['md'], SPACING['sm']))
    
    style.map('Secondary.TButton',
             background=[('active', get_color('secondary_hover')),
                        ('focus', get_color('primary_light'))])
    
    # Success button style
    style.configure('Success.TButton',
                   background=get_color('success'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0)
    
    # Danger button style
    style.configure('Danger.TButton',
                   background=get_color('error'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0)

    # Deployment (touch-friendly) button style: min ~48px height, large tap targets
    style.configure('Deployment.TButton',
                   background=get_color('primary'),
                   foreground=get_color('text_inverse'),
                   borderwidth=0,
                   focuscolor='none',
                   padding=(SPACING['xl'], 14),
                   font=('Segoe UI', 14, 'normal'))
    style.map('Deployment.TButton',
             background=[('active', get_color('primary_hover')),
                        ('focus', get_color('primary_light'))])
    
    # Entry/Combobox styles
    style.configure('TEntry',
                   fieldbackground=get_color('surface'),
                   foreground=get_color('text_primary'),
                   borderwidth=1,
                   relief='flat',
                   padding=SPACING['sm'])
    
    style.configure('TCombobox',
                   fieldbackground=get_color('surface'),
                   foreground=get_color('text_primary'),
                   borderwidth=1,
                   relief='flat')
    
    # Checkbutton style
    style.configure('TCheckbutton',
                   background=get_color('background'),
                   foreground=get_color('text_primary'),
                   focuscolor='none',
                   font=get_font('body'))
    
    # Notebook (tabs) style
    style.configure('TNotebook',
                   background=get_color('background'),
                   borderwidth=0)
    
    style.configure('TNotebook.Tab',
                   background=get_color('surface'),
                   foreground=get_color('text_secondary'),
                   padding=(SPACING['lg'], SPACING['md']),
                   borderwidth=0,
                   font=get_font('body'))
    
    style.map('TNotebook.Tab',
             background=[('selected', get_color('background')),
                        ('active', get_color('primary_light'))],
             foreground=[('selected', get_color('primary')),
                        ('active', get_color('primary'))],
             expand=[('selected', [1, 1, 1, 0])])
    
    # Progressbar style
    style.configure('TProgressbar',
                   background=get_color('primary'),
                   troughcolor=get_color('border_light'),
                   borderwidth=0,
                   lightcolor=get_color('primary'),
                   darkcolor=get_color('primary'))
    
    # Scale (slider) style
    style.configure('TScale',
                   background=get_color('background'),
                   troughcolor=get_color('border_light'),
                   borderwidth=0)
    
    # Scrollbar style
    style.configure('TScrollbar',
                   background=get_color('border'),
                   troughcolor=get_color('background'),
                   borderwidth=0,
                   arrowcolor=get_color('text_secondary'),
                   darkcolor=get_color('border'),
                   lightcolor=get_color('border'))
    
    return style

def create_card_frame(parent, **kwargs):
    """
    Create a modern card-style frame with elevation.
    
    Args:
        parent: Parent widget
        **kwargs: Additional frame arguments
    """
    frame = tk.Frame(
        parent,
        background=get_color('surface'),
        relief='flat',
        borderwidth=1,
        highlightbackground=get_color('border'),
        highlightthickness=1,
        **kwargs
    )
    return frame

def create_section_label(parent, text: str, **kwargs):
    """
    Create a modern section heading label.
    
    Args:
        parent: Parent widget
        text: Label text
        **kwargs: Additional label arguments
    """
    label = tk.Label(
        parent,
        text=text,
        font=get_font('heading_small'),
        background=get_color('background'),
        foreground=get_color('text_primary'),
        anchor='w',
        **kwargs
    )
    return label

def create_caption_label(parent, text: str, **kwargs):
    """
    Create a caption/helper text label.
    
    Args:
        parent: Parent widget
        text: Label text
        **kwargs: Additional label arguments
    """
    label = tk.Label(
        parent,
        text=text,
        font=get_font('caption'),
        background=get_color('background'),
        foreground=get_color('text_tertiary'),
        anchor='w',
        **kwargs
    )
    return label

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color."""
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def lighten_color(hex_color: str, factor: float = 0.1) -> str:
    """Lighten a color by a factor (0-1)."""
    rgb = hex_to_rgb(hex_color)
    rgb = tuple(min(255, int(c + (255 - c) * factor)) for c in rgb)
    return rgb_to_hex(rgb)

def darken_color(hex_color: str, factor: float = 0.1) -> str:
    """Darken a color by a factor (0-1)."""
    rgb = hex_to_rgb(hex_color)
    rgb = tuple(max(0, int(c * (1 - factor))) for c in rgb)
    return rgb_to_hex(rgb)

