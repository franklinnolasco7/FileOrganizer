"""Utilities for applying consistent light/dark theming to page containers."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QWidget, QScrollArea
from qfluentwidgets import isDarkTheme, FluentIcon as FIF


def get_theme_palette() -> Dict[str, str]:
    """Return the current theme palette for pages and panels."""
    dark = isDarkTheme()
    if dark:
        return {
            "page_bg": "rgb(16, 16, 18)",
            "card_bg": "rgb(40, 40, 45)",
            "border": "rgba(255, 255, 255, 0.08)",
            "panel_bg": "rgb(40, 40, 45)",
            "panel_border": "rgba(255, 255, 255, 0.08)",
            "text": "rgb(235, 235, 235)",
            "muted_text": "rgba(235, 235, 235, 0.8)",
            "disabled_text": "rgba(235, 235, 235, 0.45)",
            "button_bg": "rgb(52, 53, 58)",
            "button_hover": "rgb(64, 65, 72)",
            "button_border": "rgba(255, 255, 255, 0.12)",
            "button_disabled": "rgba(255, 255, 255, 0.07)",
            "dialog_bg": "rgb(32, 32, 36)",
            "dialog_border": "rgba(255, 255, 255, 0.12)",
            "dialog_header_bg": "rgb(45, 45, 52)",
            "title_bar_bg": "rgb(36, 36, 40)",
            "dialog_surface": "rgb(38, 39, 44)",
            "dialog_surface_alt": "rgb(45, 46, 52)",
            "accent": "rgb(0, 159, 170)",
            "accent_hover": "rgb(0, 185, 197)",
            "accent_text": "rgb(255, 255, 255)",
            "accent_soft": "rgba(0, 159, 170, 0.28)",
        }
    return {
        "page_bg": "rgb(245, 245, 245)",
        "card_bg": "rgb(255, 255, 255)",
        "border": "rgb(224, 224, 224)",
        "panel_bg": "rgb(255, 255, 255)",
        "panel_border": "rgb(224, 224, 224)",
        "text": "rgb(33, 33, 33)",
        "muted_text": "rgb(97, 97, 97)",
        "disabled_text": "rgba(33, 33, 33, 0.45)",
        "button_bg": "rgb(247, 247, 247)",
        "button_hover": "rgb(240, 240, 240)",
        "button_border": "rgb(214, 214, 214)",
        "button_disabled": "rgb(236, 236, 236)",
        "dialog_bg": "rgb(255, 255, 255)",
        "dialog_border": "rgb(225, 225, 225)",
        "dialog_header_bg": "rgb(245, 245, 245)",
        "title_bar_bg": "rgb(236, 236, 236)",
        "dialog_surface": "rgb(255, 255, 255)",
        "dialog_surface_alt": "rgb(248, 249, 250)",
        "accent": "rgb(0, 120, 212)",
        "accent_hover": "rgb(0, 140, 230)",
        "accent_text": "rgb(255, 255, 255)",
        "accent_soft": "rgba(0, 120, 212, 0.18)",
    }


def apply_page_theme(
    content_widget: QWidget,
    scroll_area: Optional[QScrollArea] = None,
    *,
    card_background: Optional[str] = None,
) -> None:
    """Apply theme-aware background styling to a page container and optional scroll area."""
    palette = get_theme_palette()
    page_bg = palette["page_bg"]
    border_color = palette["border"]
    card_bg = card_background or palette["card_bg"]

    content_widget.setStyleSheet(
        f"""
        QWidget#pageContentWidget {{
            background-color: {page_bg};
        }}
        QWidget#pageContentWidget CardWidget {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
        }}
        """
    )

    if scroll_area is not None:
        scroll_area.setStyleSheet(
            f"""
            QScrollArea#pageScrollArea,
            SmoothScrollArea#pageScrollArea {{
                background-color: {page_bg};
                border: none;
            }}
            QScrollArea#pageScrollArea QWidget,
            SmoothScrollArea#pageScrollArea QWidget {{
                background-color: {page_bg};
            }}
            """
        )


def apply_panel_theme(
    widget: QWidget,
    *,
    selector: Optional[str] = None,
    radius: int = 8,
    show_border: bool = True,
) -> None:
    """Apply panel styling (background/border) to a widget using the shared palette."""
    palette = get_theme_palette()
    sel = selector or widget.metaObject().className()
    border = f"border: 1px solid {palette['panel_border']};" if show_border else "border: none;"
    widget.setStyleSheet(
        f"""
        {sel} {{
            background-color: {palette['panel_bg']};
            {border}
            border-radius: {radius}px;
        }}
        """
    )


def _build_dialog_style(name: str, palette: Dict[str, str], radius: int, *, border_visible: bool) -> str:
    """Create base stylesheet text for dialog-like widgets."""
    border_rule = (
        f"border: 1px solid {palette['dialog_border']};"
        if border_visible
        else "border: none;"
    )
    return (
        f"""
        QWidget#{name} {{
            background-color: {palette['dialog_bg']};
            {border_rule}
            border-radius: {radius}px;
            color: {palette['text']};
        }}
        QWidget#{name} QLabel,
        QWidget#{name} TitleLabel,
        QWidget#{name} SubtitleLabel,
        QWidget#{name} BodyLabel,
        QWidget#{name} StrongBodyLabel,
        QWidget#{name} CaptionLabel {{
            color: {palette['text']};
        }}
        """
    )


def apply_dialog_theme(
    dialog: QWidget,
    *,
    object_name: Optional[str] = None,
    radius: int = 12,
    border_visible: bool = True,
) -> None:
    """Apply shared palette styling to a dialog window."""
    palette = get_theme_palette()
    name = object_name or dialog.objectName() or "appDialog"
    dialog.setObjectName(name)
    dialog.setStyleSheet(_build_dialog_style(name, palette, radius, border_visible=border_visible))


def apply_message_box_theme(box: QWidget, *, radius: int = 12) -> None:
    """Apply consistent styling to qfluentwidgets MessageBox instances."""
    palette = get_theme_palette()
    name = box.objectName() or "appMessageBox"
    box.setObjectName(name)

    target = getattr(box, "widget", None) or getattr(box, "view", None) or box
    target_name = name if target is box else f"{name}View"
    target.setObjectName(target_name)

    base = _build_dialog_style(target_name, palette, radius, border_visible=True)
    button_styles = f"""
    QWidget#{target_name} QPushButton {{
        background-color: {palette['button_bg']};
        border: 1px solid {palette['button_border']};
        color: {palette['text']};
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QWidget#{target_name} QPushButton:hover {{
        background-color: {palette['button_hover']};
    }}
    QWidget#{target_name} QPushButton:disabled {{
        background-color: {palette['button_disabled']};
        color: {palette['disabled_text']};
        border-color: {palette['button_disabled']};
    }}
    """
    target.setStyleSheet(base + button_styles)


def _find_icon_file() -> Optional[Path]:
    """Locate the brand icon within assets directory, supporting common extensions."""
    assets_dir = Path(__file__).resolve().parents[2] / "assets"
    for ext in (".png", ".ico", ".jpg", ".jpeg", ".svg"):
        candidate = assets_dir / f"icon{ext}"
        if candidate.exists():
            return candidate
    return None


@lru_cache(maxsize=1)
def get_brand_icon() -> QIcon:
    """Return the project's brand icon, falling back to Fluent folder icon when missing."""
    icon_path = _find_icon_file()
    if icon_path:
        pixmap = QPixmap(str(icon_path))
        if not pixmap.isNull():
            icon = QIcon()
            for size in (16, 20, 24, 32, 48, 64, 96, 128, 192, 256):
                scaled = pixmap.scaled(
                    size,
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                icon.addPixmap(scaled)
            return icon
    return QIcon(FIF.FOLDER.icon())
