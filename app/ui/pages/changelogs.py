"""Changelogs page showing version history and updates."""
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt

from qfluentwidgets import (
    CardWidget, BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel,
    SmoothScrollArea, isDarkTheme
)
from qfluentwidgets import FluentIcon as FIF


class ChangelogsPage:
    """Changelogs page showing version history"""
    
    def __init__(self) -> None:
        """Initialize changelogs page"""
        self.date_labels = []  # Store date labels for theme updates
    
    def _create_card(self, margins=(16, 16, 16, 16), spacing=12):
        """Helper method to create a CardWidget with consistent layout
        
        Args:
            margins: Tuple of (left, top, right, bottom) margins
            spacing: Spacing between layout items
            
        Returns:
            Tuple of (card, card_layout)
        """
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*margins)
        card_layout.setSpacing(spacing)
        return card, card_layout
    
    def create(self) -> QWidget:
        """Create changelogs page widget
        
        Returns:
            Changelogs page widget
        """
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScrollArea")
        
        widget = QWidget()
        widget.setObjectName("pageContentWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 24, 32, 24)
        layout.setSpacing(20)
        
        layout.addWidget(TitleLabel("Changelogs"))
        
        # Version 2.7.1
        layout.addWidget(self._create_version_card("2.7.1", "November 2025", [
            "Improved code documentation across all modules",
        ]))
        
        # Version 2.7.0
        layout.addWidget(self._create_version_card("2.7.0", "November 2025", [
            "Added export activity log feature",
            "Configurable log export directory in settings",
        ]))
        
        # Version 2.6.0
        layout.addWidget(self._create_version_card("2.6.0", "November 2025", [
            "Added file size filter feature",
            "Set minimum and maximum file size limits (in KB)",
            "Skip files that don't meet size criteria",
        ]))
        
        # Version 2.5.0
        layout.addWidget(self._create_version_card("2.5.0", "November 2025", [
            "Added duplicate file handling options can be configured in settings",
            "Choose between rename, skip, or replace duplicates",
        ]))

        # Version 2.4.0
        layout.addWidget(self._create_version_card("2.4.0", "November 2025", [
            "Added custom categories support",
            "Allows users to add and remove custom file categories"
        ]))

        # Version 2.3.0
        layout.addWidget(self._create_version_card("2.3.0", "November 2025", [
            "Fixed nested folder organization",
            "Auto-cleanup empty folders after moving files",
            "Recursive file scanning in subdirectories",
        ]))

        # Version 2.2.0
        layout.addWidget(self._create_version_card("2.2.0", "November 2025", [
            "Added Settings tab with persistent folder paths",
            "Added About & Changelogs pages",
            "Auto-save feature for last used folders",
        ]))
        
        # Version 2.1.0
        layout.addWidget(self._create_version_card("2.1.0", "November 2025", [
            "Added file preview before organizing",
            "Added undo feature",
            "Color-coded activity log",
            "Drag & drop for folders",
        ]))
        
        # Version 2.0.0
        layout.addWidget(self._create_version_card("2.0.0", "November 2025", [
            "Complete UI redesign with dark theme",
            "Multi-tab interface",
            "File organization by category",
        ]))
        
        # Version 1.0.0
        layout.addWidget(self._create_version_card("1.0.0", "November 2025", [
            "Initial release",
        ]))
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_version_card(self, version: str, date: str, changes: list) -> CardWidget:
        """Create version card with changelog."""
        card, card_layout = self._create_card()
        
        # Version header
        version_layout = QHBoxLayout()
        version_label = SubtitleLabel(f"v{version}")
        date_label = CaptionLabel(date)
        date_label.setStyleSheet("color: gray;")
        self.date_labels.append(date_label)
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        version_layout.addWidget(date_label)
        card_layout.addLayout(version_layout)
        
        # Changes list
        for change in changes:
            card_layout.addWidget(BodyLabel(f"• {change}"))
        
        return card
    
    def apply_date_label_theme(self) -> None:
        """Apply theme-aware styling to date labels"""
        # Light mode: darker gray, Dark mode: lighter gray
        color = "rgb(153, 153, 153)" if not isDarkTheme() else "rgb(176, 176, 176)"
        for label in self.date_labels:
            label.setStyleSheet(f"color: {color}; font-size: 11px;")


