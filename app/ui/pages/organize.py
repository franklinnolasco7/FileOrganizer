"""Main organize page for file organization operations."""
from typing import List
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt

from qfluentwidgets import (
    PushButton, PrimaryPushButton, CheckBox,
    BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel,
    DoubleSpinBox, SmoothScrollArea, ToolTipFilter, isDarkTheme
)
from qfluentwidgets import FluentIcon as FIF

from app.core.constants import FileCategory, CUSTOM_CATEGORIES
from app.ui.widgets import DragDropLineEdit, ColoredPlainTextEdit, ThemedCardWidget
from app.ui.theme_utils import apply_page_theme


class OrganizePage:
    """File organization page with source/dest/category inputs and live log."""
    
    def __init__(
        self,
        on_organize,
        on_browse_source,
        on_browse_dest,
        on_clear_log,
        on_undo=None,
        on_preview=None,
        on_export_log=None,
    ) -> None:
        """Initialize organize page with callbacks."""
        self.on_organize = on_organize
        self.on_browse_source = on_browse_source
        self.on_browse_dest = on_browse_dest
        self.on_clear_log = on_clear_log
        self.on_undo = on_undo or (lambda: None)
        self.on_preview = on_preview or (lambda: None)
        self.on_export_log = on_export_log or (lambda: None)
        self.hint_labels = []  # Store hint labels for theme updates
        self.scroll_area = None
        self.content_widget = None

    def _create_card(self, margins=(12, 16, 12, 16), spacing=16):
        """Helper method to create a CardWidget with consistent layout
        
        Args:
            margins: Tuple of (left, top, right, bottom) margins
            spacing: Spacing between layout items
            
        Returns:
            Tuple of (card, card_layout)
        """
        card = ThemedCardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(*margins)
        card_layout.setSpacing(spacing)
        return card, card_layout

    def create(self) -> QWidget:
        """Create organize page widget"""
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScrollArea")

        widget = QWidget()
        widget.setObjectName("pageContentWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 24, 32, 24)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("Organize Files"))
        layout.addWidget(self._create_source_card())
        layout.addWidget(self._create_dest_card())
        layout.addWidget(self._create_category_card())
        layout.addWidget(self._create_size_filter_card())
        layout.addWidget(self._create_log_card())
        layout.addLayout(self._create_button_layout())
        layout.addStretch()

        scroll.setWidget(widget)
        self.root_widget = scroll
        self.scroll_area = scroll
        self.content_widget = widget
        apply_page_theme(widget, scroll)
        return scroll

    def _create_source_card(self) -> ThemedCardWidget:
        """Create source folder selection card with drag-drop support"""
        card, layout = self._create_card(margins=(16, 16, 16, 16), spacing=10)

        label_layout = QHBoxLayout()
        label_layout.addWidget(StrongBodyLabel("Source Folder"))
        
        hint_label = CaptionLabel("Drag & drop")
        self.hint_labels.append(hint_label)
        label_layout.addStretch()
        label_layout.addWidget(hint_label)
        layout.addLayout(label_layout)

        input_layout = QHBoxLayout()
        self.source_input = DragDropLineEdit()
        self.source_input.setObjectName("source_input")
        self.source_input.setPlaceholderText("Select or drag source folder...")
        input_layout.addWidget(self.source_input, 1)

        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.setFixedSize(100, 32)
        browse_btn.clicked.connect(self.on_browse_source)
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        return card

    def _create_dest_card(self) -> ThemedCardWidget:
        """Create destination folder selection card with drag-drop support"""
        card, layout = self._create_card(margins=(16, 16, 16, 16), spacing=10)

        label_layout = QHBoxLayout()
        label_layout.addWidget(StrongBodyLabel("Destination Folder"))
        
        hint_label = CaptionLabel("Drag & drop")
        self.hint_labels.append(hint_label)
        label_layout.addStretch()
        label_layout.addWidget(hint_label)
        layout.addLayout(label_layout)

        input_layout = QHBoxLayout()
        self.dest_input = DragDropLineEdit()
        self.dest_input.setObjectName("dest_input")
        self.dest_input.setPlaceholderText("Select or drag destination folder...")
        input_layout.addWidget(self.dest_input, 1)

        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.setFixedSize(100, 32)
        browse_btn.clicked.connect(self.on_browse_dest)
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        return card

    def _create_category_card(self) -> ThemedCardWidget:
        """Create file category selection card"""
        card, layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)

        header_layout = QHBoxLayout()
        category_label = StrongBodyLabel("File Categories")
        header_layout.addWidget(category_label)
        
        select_all_btn = PushButton("Select All")
        select_all_btn.setFixedSize(90, 32)
        select_all_btn.clicked.connect(self._select_all_categories)
        header_layout.addWidget(select_all_btn)
        
        deselect_all_btn = PushButton("Deselect All")
        deselect_all_btn.setFixedSize(100, 32)
        deselect_all_btn.clicked.connect(self._deselect_all_categories)
        header_layout.addWidget(deselect_all_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)

        check_layout = QHBoxLayout()
        self.category_checks: dict = {}

        for cat in FileCategory:
            if cat.name != "OTHERS":
                check = CheckBox(cat.value)
                check.setChecked(True)
                self.category_checks[cat] = check
                check_layout.addWidget(check)

        check_layout.addStretch()
        layout.addLayout(check_layout)
        return card
    
    def _create_size_filter_card(self) -> ThemedCardWidget:
        """Create file size filter card"""
        card, layout = self._create_card(margins=(16, 16, 16, 16), spacing=12)
        
        # Header with enable checkbox
        header_layout = QHBoxLayout()
        self.enable_size_filter_check = CheckBox("Enable File Size Filter")
        self.enable_size_filter_check.setChecked(False)
        self.enable_size_filter_check.toggled.connect(self._toggle_size_filter)
        header_layout.addWidget(self.enable_size_filter_check)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Min/Max size inputs
        size_layout = QHBoxLayout()
        
        # Min size
        min_layout = QVBoxLayout()
        min_layout.addWidget(BodyLabel("Minimum Size (KB)"))
        self.min_size_input = DoubleSpinBox()
        self.min_size_input.setRange(0, 999999999)
        self.min_size_input.setValue(0)
        self.min_size_input.setDecimals(2)
        self.min_size_input.setSingleStep(1)
        self.min_size_input.setMinimumWidth(150)
        self.min_size_input.setEnabled(False)
        self.min_size_input.setToolTip("Files smaller than this will be skipped (0 = no minimum)")
        self.min_size_input.installEventFilter(ToolTipFilter(self.min_size_input))
        min_layout.addWidget(self.min_size_input)
        size_layout.addLayout(min_layout)
        
        size_layout.addSpacing(20)
        
        # Max size
        max_layout = QVBoxLayout()
        max_layout.addWidget(BodyLabel("Maximum Size (KB)"))
        self.max_size_input = DoubleSpinBox()
        self.max_size_input.setRange(0, 999999999)
        self.max_size_input.setValue(0)
        self.max_size_input.setDecimals(2)
        self.max_size_input.setSingleStep(1)
        self.max_size_input.setMinimumWidth(150)
        self.max_size_input.setEnabled(False)
        self.max_size_input.setToolTip("Files larger than this will be skipped (0 = no maximum)")
        self.max_size_input.installEventFilter(ToolTipFilter(self.max_size_input))
        max_layout.addWidget(self.max_size_input)
        size_layout.addLayout(max_layout)
        
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        return card
    
    def _toggle_size_filter(self, enabled: bool) -> None:
        """Enable/disable size filter inputs"""
        self.min_size_input.setEnabled(enabled)
        self.max_size_input.setEnabled(enabled)
    
    def _select_all_categories(self) -> None:
        """Select all category checkboxes"""
        for check in self.category_checks.values():
            check.setChecked(True)
    
    def _deselect_all_categories(self) -> None:
        """Deselect all category checkboxes"""
        for check in self.category_checks.values():
            check.setChecked(False)

    def _create_log_card(self) -> ThemedCardWidget:
        """Create activity log card"""
        card, layout = self._create_card(margins=(16, 16, 16, 16), spacing=10)

        header_layout = QHBoxLayout()
        header_layout.addWidget(StrongBodyLabel("Activity Log"))
        
        hint_label = CaptionLabel("Live activity")
        self.hint_labels.append(hint_label)
        header_layout.addStretch()
        header_layout.addWidget(hint_label)
        layout.addLayout(header_layout)

        self.log_text = ColoredPlainTextEdit()
        self.log_text.setObjectName("activityLogTextEdit")
        layout.addWidget(self.log_text, 1)

        return card

    def _create_button_layout(self) -> QHBoxLayout:
        """Create action button layout with visual grouping"""
        layout = QHBoxLayout()
        layout.setSpacing(10)

        # Primary actions group
        # Preview button
        self.preview_btn = PushButton(FIF.VIEW, "Preview")
        self.preview_btn.setFixedSize(110, 36)
        self.preview_btn.clicked.connect(self.on_preview)
        layout.addWidget(self.preview_btn)

        # Organize button (Primary action)
        self.organize_btn = PrimaryPushButton(FIF.SYNC, "Organize Files")
        self.organize_btn.setFixedSize(150, 36)
        self.organize_btn.clicked.connect(self.on_organize)
        layout.addWidget(self.organize_btn)

        # Undo button
        self.undo_btn = PushButton(FIF.RETURN, "Undo")
        self.undo_btn.setFixedSize(90, 36)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.on_undo)
        layout.addWidget(self.undo_btn)

        layout.addSpacing(20)  # Visual separator

        # Secondary actions group
        # Clear Log button
        clear_btn = PushButton(FIF.DELETE, "Clear Log")
        clear_btn.setFixedSize(110, 36)
        clear_btn.clicked.connect(self.on_clear_log)
        layout.addWidget(clear_btn)
        
        # Export Log button
        export_btn = PushButton(FIF.SAVE, "Export Log")
        export_btn.setFixedSize(120, 36)
        export_btn.clicked.connect(self.on_export_log)
        layout.addWidget(export_btn)

        layout.addStretch()
        return layout

    def set_undo_enabled(self, enabled: bool) -> None:
        """Enable or disable undo button"""
        if hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(enabled)

    def set_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all action buttons during processing
        
        Args:
            enabled: True to enable buttons, False to disable
        """
        if hasattr(self, 'preview_btn'):
            self.preview_btn.setEnabled(enabled)
        if hasattr(self, 'organize_btn'):
            self.organize_btn.setEnabled(enabled)
        # Note: undo button state is managed separately based on history

    def get_source(self) -> str:
        """Get source folder path"""
        return self.source_input.text()

    def get_destination(self) -> str:
        """Get destination folder path"""
        return self.dest_input.text()

    def get_active_categories(self) -> list:
        """Get selected categories"""
        return [cat for cat, check in self.category_checks.items() if check.isChecked()]
    
    def get_size_filter_settings(self) -> dict:
        """Get size filter settings"""
        return {
            'enabled': self.enable_size_filter_check.isChecked(),
            'min_size_kb': self.min_size_input.value(),
            'max_size_kb': self.max_size_input.value()
        }

    def append_log(self, message: str) -> None:
        """Append colored message to log"""
        self.log_text.append_colored(message)

    def clear_log(self) -> None:
        """Clear log display"""
        self.log_text.clear()
    
    def get_log_content(self) -> str:
        """Get current log content as plain text"""
        return self.log_text.toPlainText()
    
    def apply_hint_label_theme(self) -> None:
        """Apply theme-aware styling to hint labels"""
        # Light mode: darker gray, Dark mode: lighter gray
        color = "rgb(153, 153, 153)" if not isDarkTheme() else "rgb(176, 176, 176)"
        for label in self.hint_labels:
            label.setStyleSheet(f"color: {color}; font-size: 11px;")


