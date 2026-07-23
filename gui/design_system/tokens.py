"""
Presentation Layer - Mackanized flasher V1 Design Tokens

Defines design system tokens for Mackanized flasher V1 Blank Canvas Architecture:
- Calm Dark Slate Surface Hierarchy (#181A20, #20232B, #292C36, #333744)
- Precision Accent Blue Palette (#2563EB, #3B82F6, #1D4ED8)
- Minimal Soft Border Tokens (#2D323E)
- 6px / 8px Rounded Corner Radii
- Inter & Segoe UI Variable Typography Scales
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokens:
    """Mackanized flasher V1 Color Tokens."""

    canvas_base: str          = "#181A20"  # Base Window Canvas
    surface_card: str         = "#20232B"  # Elevated Container Card
    surface_control: str      = "#292C36"  # Control Input & Button Base
    surface_hover: str        = "#333744"  # Subtle Interactive Hover Fill
    surface_pressed: str      = "#1B1D24"  # Active Pressed State
    surface_selected: str     = "#1E293B"  # Quiet Selection Highlight
    surface_disabled: str     = "#1C1E24"

    border_subtle: str        = "rgba(255, 255, 255, 0.04)"  # Soft borderless divider
    border_default: str       = "rgba(255, 255, 255, 0.08)"  # Subtle control outline
    border_strong: str        = "rgba(255, 255, 255, 0.15)"  # Quiet focus outline
    border_focus: str         = "#3B82F6"  # Precision Focus Ring

    text_primary: str         = "#F1F5F9"  # High contrast text
    text_secondary: str       = "#94A3B8"  # Subtitle & helper label
    text_muted: str           = "#64748B"  # Muted / disabled text
    text_disabled: str        = "#475569"
    text_on_accent: str       = "#FFFFFF"

    accent_primary: str       = "#2563EB"
    accent_hover: str         = "#3B82F6"
    accent_pressed: str       = "#1D4ED8"
    accent_soft: str          = "#1E3A8A"
    accent_border: str        = "#2563EB"

    success_soft: str         = "#064E3B"
    success_border: str       = "#059669"
    success_text: str         = "#6EE7B7"

    warning_soft: str         = "#78350F"
    warning_border: str       = "#D97706"
    warning_text: str         = "#FDE68A"

    danger_soft: str          = "#7F1D1D"
    danger_border: str        = "#DC2626"
    danger_text: str          = "#FCA5A5"

    phase_prepare: str        = "#3B82F6"
    phase_unlock: str         = "#8B5CF6"
    phase_erase: str          = "#EC4899"
    phase_write: str          = "#F97316"
    phase_verify: str         = "#14B8A6"
    phase_complete: str       = "#10B981"


@dataclass(frozen=True)
class TypographyTokens:
    """Inter & Segoe UI Variable Typography Scale."""

    font_family_main: str = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
    font_family_mono: str = "'SF Mono', 'JetBrains Mono', 'Menlo', 'Monaco', 'Consolas', monospace"

    size_caption: int  = 11
    size_body_sm: int  = 12
    size_body: int     = 12
    size_subtitle: int = 14
    size_title: int    = 16
    size_header: int   = 20

    weight_regular: int = 400
    weight_medium: int  = 500
    weight_semi: int    = 600
    weight_bold: int    = 700


@dataclass(frozen=True)
class SpacingGrid:
    """8pt Layout Grid Tokens."""

    space_2: int  = 2
    space_4: int  = 4
    space_8: int  = 8
    space_12: int = 12
    space_16: int = 16
    space_24: int = 24
    radius_sm: int = 6   # 6px Corner Radius
    radius_md: int = 8   # 8px Corner Radius
