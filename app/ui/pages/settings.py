"""Settings page for configuring application preferences and custom categories."""
from pathlib import Path
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget, QFileDialog, QButtonGroup
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtCore import QUrl

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit, CheckBox,
    BodyLabel, TitleLabel, SubtitleLabel, CaptionLabel, Theme,
    SpinBox, DoubleSpinBox, SmoothScrollArea,
    InfoBar, InfoBarPosition, ToolTipFilter, isDarkTheme,
    RadioButton, MessageBox, ComboBox
)
from qfluentwidgets import FluentIcon as FIF

from app.config.config_manager import ConfigManager
from app.ui.theme_utils import apply_page_theme, apply_message_box_theme
from app.ui.widgets import ThemedCardWidget


class SettingsPage:
    """Settings panel for user preferences and custom categories"""
    
    def __init__(self, config: ConfigManager, on_close, parent=None) -> None:
        """Initialize settings page
        
        Args:
            config: Configuration manager
            on_close: Close callback function
            parent: Parent widget for dialogs
        """
        self.config = config
        self.on_close = on_close
        self._parent = parent
        self.content_widget = None
        self.scroll_area = None
    
    def _show_info_bar(self, title: str, content: str) -> None:
        """Helper method to show success InfoBar with consistent styling
        
        Args:
            title: InfoBar title
            content: InfoBar content message
        """
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self._parent
        )
    
    def _create_card(self, margins=(12, 12, 12, 12), spacing=12):
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
        """Create settings page widget
        
        Returns:
            Settings page widget
        """
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScrollArea")
        
        widget = QWidget()
        widget.setObjectName("pageContentWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 24, 32, 24)
        layout.setSpacing(20)
        
        layout.addWidget(TitleLabel("Settings"))
        
        layout.addWidget(self._create_theme_card())
        layout.addWidget(self._create_persistent_paths_card())
        layout.addWidget(self._create_duplicate_handling_card())
        layout.addWidget(self._create_size_filter_settings_card())
        layout.addWidget(self._create_recovery_backup_card())
        layout.addWidget(self._create_log_export_card())
        layout.addWidget(self._create_custom_categories_card())
        
        # Single Apply Changes button at the bottom
        apply_btn = PrimaryPushButton(FIF.ACCEPT, "Apply Changes")
        apply_btn.setFixedSize(160, 36)
        apply_btn.clicked.connect(self._apply_all_settings)
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        self.scroll_area = scroll
        self.content_widget = widget
        apply_page_theme(widget, scroll)
        return scroll

    def _create_theme_card(self) -> ThemedCardWidget:
        """Create card for theme selection."""
        card, card_layout = self._create_card()
        
        subtitle = SubtitleLabel("Appearance")
        card_layout.addWidget(subtitle)
        
        theme_layout = QHBoxLayout()
        theme_label = BodyLabel("Theme")
        
        self.theme_combo = ComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentIndex(0 if self._parent.current_theme == Theme.LIGHT else 1)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.theme_combo.setMinimumWidth(150)
        
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch()
        
        card_layout.addLayout(theme_layout)
        
        return card

    def _create_persistent_paths_card(self) -> ThemedCardWidget:
        """Create card for persistent folder path settings."""
        card, card_layout = self._create_card()
        
        card_layout.addWidget(SubtitleLabel("Persistent Paths"))
        
        from qfluentwidgets import TransparentToolButton
        
        src_layout = QHBoxLayout()
        src_label = BodyLabel("Last Source Folder")
        self.src_input = LineEdit()
        self.src_input.setPlaceholderText("Enter last used source path")
        self.src_input.setText(self.config.get("last_source_folder", ""))
        src_layout.addWidget(src_label)
        src_layout.addWidget(self.src_input, 1)
        
        src_open_btn = TransparentToolButton(FIF.LINK, self._parent)
        src_open_btn.setFixedSize(32, 32)
        src_open_btn.setToolTip("Open Source Folder")
        src_open_btn.installEventFilter(ToolTipFilter(src_open_btn, showDelay=300))
        src_open_btn.clicked.connect(self._open_source_folder)
        src_layout.addWidget(src_open_btn)
        
        card_layout.addLayout(src_layout)
        
        dst_layout = QHBoxLayout()
        dst_label = BodyLabel("Last Destination Folder")
        self.dst_input = LineEdit()
        self.dst_input.setPlaceholderText("Enter last used destination path")
        self.dst_input.setText(self.config.get("last_destination_folder", ""))
        dst_layout.addWidget(dst_label)
        dst_layout.addWidget(self.dst_input, 1)
        
        dst_open_btn = TransparentToolButton(FIF.LINK, self._parent)
        dst_open_btn.setFixedSize(32, 32)
        dst_open_btn.setToolTip("Open Destination Folder")
        dst_open_btn.installEventFilter(ToolTipFilter(dst_open_btn, showDelay=300))
        dst_open_btn.clicked.connect(self._open_destination_folder)
        dst_layout.addWidget(dst_open_btn)
        
        card_layout.addLayout(dst_layout)
        
        self.auto_save_cb = CheckBox("Auto-save on change (auto-fill paths on startup)")
        self.auto_save_cb.setChecked(self.config.get("auto_save_paths", True))
        card_layout.addWidget(self.auto_save_cb)
        
        return card

    def _create_duplicate_handling_card(self) -> ThemedCardWidget:
        """Create card for duplicate file handling settings."""
        card, card_layout = self._create_card()
        
        card_layout.addWidget(SubtitleLabel("Duplicate File Handling"))
        
        # Radio buttons for duplicate strategy
        self.duplicate_group = QButtonGroup()
        
        self.rename_radio = RadioButton("Rename duplicates (file_1.txt, file_2.txt)")
        self.skip_radio = RadioButton("Skip duplicates (keep existing)")
        self.replace_radio = RadioButton("Replace duplicates (overwrite existing)")
        
        self.duplicate_group.addButton(self.rename_radio, 0)
        self.duplicate_group.addButton(self.skip_radio, 1)
        self.duplicate_group.addButton(self.replace_radio, 2)
        
        # Set current selection
        current = self.config.get("duplicate_handling", "rename")
        if current == "rename":
            self.rename_radio.setChecked(True)
        elif current == "skip":
            self.skip_radio.setChecked(True)
        elif current == "replace":
            self.replace_radio.setChecked(True)
        
        card_layout.addWidget(self.rename_radio)
        card_layout.addWidget(self.skip_radio)
        card_layout.addWidget(self.replace_radio)
        
        return card

    def _save_duplicate_handling(self) -> None:
        """Save duplicate handling preference"""
        if self.rename_radio.isChecked():
            strategy = "rename"
        elif self.skip_radio.isChecked():
            strategy = "skip"
        elif self.replace_radio.isChecked():
            strategy = "replace"
        else:
            strategy = "rename"
        
        self.config.set("duplicate_handling", strategy, persist=False)

    def _create_size_filter_settings_card(self) -> ThemedCardWidget:
        """Create card for file size filter default settings."""
        card, card_layout = self._create_card()
        
        card_layout.addWidget(SubtitleLabel("File Size Filter Defaults"))
        
        # Enable filter checkbox
        self.settings_enable_filter = CheckBox("Enable size filter by default")
        self.settings_enable_filter.setChecked(self.config.get("enable_size_filter", False))
        card_layout.addWidget(self.settings_enable_filter)
        
        # Min size setting
        min_layout = QHBoxLayout()
        min_label = BodyLabel("Default Minimum Size (KB)")
        self.settings_min_size = DoubleSpinBox()
        self.settings_min_size.setRange(0, 999999999)
        self.settings_min_size.setValue(self.config.get("min_file_size_kb", 0))
        self.settings_min_size.setDecimals(2)
        self.settings_min_size.setSingleStep(1)
        self.settings_min_size.setMinimumWidth(150)
        min_layout.addWidget(min_label)
        min_layout.addWidget(self.settings_min_size)
        min_layout.addStretch()
        card_layout.addLayout(min_layout)
        
        # Max size setting
        max_layout = QHBoxLayout()
        max_label = BodyLabel("Default Maximum Size (KB)")
        self.settings_max_size = DoubleSpinBox()
        self.settings_max_size.setRange(0, 999999999)
        self.settings_max_size.setValue(self.config.get("max_file_size_kb", 0))
        self.settings_max_size.setDecimals(2)
        self.settings_max_size.setSingleStep(1)
        self.settings_max_size.setMinimumWidth(150)
        max_layout.addWidget(max_label)
        max_layout.addWidget(self.settings_max_size)
        max_layout.addStretch()
        card_layout.addLayout(max_layout)
        
        return card
    
    def _save_size_filter_settings(self) -> None:
        """Save file size filter settings"""
        enable_filter = self.settings_enable_filter.isChecked()
        min_size = self.settings_min_size.value()
        max_size = self.settings_max_size.value()
        
        self.config.set("enable_size_filter", enable_filter, persist=False)
        self.config.set("min_file_size_kb", min_size, persist=False)
        self.config.set("max_file_size_kb", max_size, persist=False)

    def _create_log_export_card(self) -> ThemedCardWidget:
        """Create card for activity log export directory settings."""
        card, card_layout = self._create_card()
        
        card_layout.addWidget(SubtitleLabel("Activity Log Export"))
        
        # Export directory setting
        dir_layout = QHBoxLayout()
        dir_label = BodyLabel("Default Export Directory")
        self.log_export_dir_input = LineEdit()
        self.log_export_dir_input.setPlaceholderText("Select directory for log exports")
        self.log_export_dir_input.setText(self.config.get("log_export_directory", str(Path.home())))
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.log_export_dir_input, 1)
        
        # Open folder button (icon only with tooltip)
        from qfluentwidgets import TransparentToolButton
        open_log_btn = TransparentToolButton(FIF.LINK, self._parent)
        open_log_btn.setFixedSize(32, 32)
        open_log_btn.setToolTip("Open Export Folder")
        open_log_btn.installEventFilter(ToolTipFilter(open_log_btn, showDelay=300))
        open_log_btn.clicked.connect(self._open_log_export_folder)
        dir_layout.addWidget(open_log_btn)
        
        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.setFixedSize(100, 32)
        browse_btn.clicked.connect(self._browse_log_export_dir)
        dir_layout.addWidget(browse_btn)
        card_layout.addLayout(dir_layout)
        
        return card
    
    def _browse_log_export_dir(self) -> None:
        """Browse for log export directory."""
        folder = QFileDialog.getExistingDirectory(None, "Select Log Export Directory")
        if folder:
            self.log_export_dir_input.setText(folder)
    
    def _open_log_export_folder(self) -> None:
        """Open the log export folder in file explorer."""
        export_path = Path(self.log_export_dir_input.text()).expanduser().resolve()
        if export_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(export_path)))
        else:
            InfoBar.warning(
                title="Folder Not Found",
                content="The specified directory does not exist.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
    
    def _save_log_export_settings(self) -> None:
        """Save log export directory settings"""
        export_dir = self.log_export_dir_input.text().strip()
        
        if export_dir and not Path(export_dir).exists():
            w = MessageBox("Invalid Directory", "The specified directory does not exist.", self._parent)
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return
        
        if not export_dir:
            export_dir = str(Path.home())
        
        self.config.set("log_export_directory", export_dir, persist=False)

    def _create_recovery_backup_card(self) -> ThemedCardWidget:
        """Create card for recovery backup settings."""
        card, card_layout = self._create_card()
        
        card_layout.addWidget(SubtitleLabel("Recovery Backup"))
        
        # Enable recovery backup checkbox
        self.enable_recovery_cb = CheckBox("Enable automatic recovery backups before organizing")
        self.enable_recovery_cb.setChecked(self.config.get("enable_recovery_backup", True))
        self.enable_recovery_cb.stateChanged.connect(self._on_recovery_enabled_changed)
        card_layout.addWidget(self.enable_recovery_cb)
        
        # Recovery folder location
        folder_layout = QHBoxLayout()
        folder_label = BodyLabel("Backup Location")
        
        self.recovery_folder_input = LineEdit()
        self.recovery_folder_input.setPlaceholderText("Select folder for recovery backups")
        default_recovery = str(Path.home() / "FileOrganizer_Recovery")
        self.recovery_folder_input.setText(self.config.get("recovery_backup_folder", default_recovery))
        self.recovery_folder_input.setEnabled(self.enable_recovery_cb.isChecked())
        
        folder_layout.addWidget(folder_label)
        folder_layout.addWidget(self.recovery_folder_input, 1)
        
        # Open folder button (icon only with tooltip)
        from qfluentwidgets import TransparentToolButton
        open_btn = TransparentToolButton(FIF.LINK, self._parent)
        open_btn.setFixedSize(32, 32)
        open_btn.setToolTip("Open Recovery Folder")
        open_btn.installEventFilter(ToolTipFilter(open_btn, showDelay=300))
        open_btn.clicked.connect(self._open_recovery_folder)
        open_btn.setEnabled(self.enable_recovery_cb.isChecked())
        self.recovery_open_btn = open_btn
        folder_layout.addWidget(open_btn)
        
        browse_btn = PushButton(FIF.FOLDER, "Browse")
        browse_btn.setFixedSize(100, 32)
        browse_btn.clicked.connect(self._browse_recovery_folder)
        browse_btn.setEnabled(self.enable_recovery_cb.isChecked())
        self.recovery_browse_btn = browse_btn
        folder_layout.addWidget(browse_btn)
        
        card_layout.addLayout(folder_layout)
        
        # Backup size limit setting
        size_layout = QHBoxLayout()
        size_label = BodyLabel("Backup Size Limit (GB)")
        
        self.backup_size_spin = DoubleSpinBox()
        self.backup_size_spin.setRange(0.1, 100.0)
        self.backup_size_spin.setSingleStep(0.5)
        self.backup_size_spin.setDecimals(1)
        self.backup_size_spin.setValue(self.config.get("recovery_backup_size_limit_gb", 5.0))
        self.backup_size_spin.setMinimumWidth(150)
        self.backup_size_spin.setEnabled(self.enable_recovery_cb.isChecked())
        
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.backup_size_spin)
        
        # Show available space
        recovery_path = Path(self.config.get("recovery_backup_folder", str(Path.home() / "FileOrganizer_Recovery")))
        available_space = self._get_available_space(recovery_path)
        space_label = CaptionLabel(f"(Available: {available_space:.1f} GB)")
        color = "rgb(153, 153, 153)" if not isDarkTheme() else "rgb(176, 176, 176)"
        space_label.setStyleSheet(f"color: {color};")
        self.recovery_space_label = space_label
        size_layout.addWidget(space_label)
        size_layout.addStretch()
        
        card_layout.addLayout(size_layout)
        
        # Retention days setting
        retention_layout = QHBoxLayout()
        retention_label = BodyLabel("Keep Backups For (Days)")
        
        self.retention_spin = SpinBox()
        self.retention_spin.setRange(1, 365)
        self.retention_spin.setValue(self.config.get("recovery_backup_retention_days", 30))
        self.retention_spin.setMinimumWidth(150)
        self.retention_spin.setEnabled(self.enable_recovery_cb.isChecked())
        
        retention_layout.addWidget(retention_label)
        retention_layout.addWidget(self.retention_spin)
        
        info_label = CaptionLabel("(Auto-deleted after this period)")
        color = "rgb(153, 153, 153)" if not isDarkTheme() else "rgb(176, 176, 176)"
        info_label.setStyleSheet(f"color: {color};")
        self.retention_info_label = info_label
        retention_layout.addWidget(info_label)
        retention_layout.addStretch()
        
        card_layout.addLayout(retention_layout)
        
        return card
    
    def _on_recovery_enabled_changed(self) -> None:
        """Handle recovery backup enable/disable."""
        enabled = self.enable_recovery_cb.isChecked()
        self.recovery_folder_input.setEnabled(enabled)
        self.recovery_browse_btn.setEnabled(enabled)
        self.recovery_open_btn.setEnabled(enabled)
        self.backup_size_spin.setEnabled(enabled)
        self.retention_spin.setEnabled(enabled)
    
    def _browse_recovery_folder(self) -> None:
        """Browse for recovery backup folder."""
        folder = QFileDialog.getExistingDirectory(None, "Select Recovery Backup Folder")
        if folder:
            self.recovery_folder_input.setText(folder)
    
    def _open_recovery_folder(self) -> None:
        """Open the recovery folder in file explorer."""
        recovery_path = Path(self.recovery_folder_input.text()).expanduser().resolve()
        if recovery_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(recovery_path)))
        else:
            InfoBar.warning(
                title="Folder Not Found",
                content="The recovery folder doesn't exist yet. It will be created after the first organize operation.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
    
    def _open_source_folder(self) -> None:
        """Open the source folder in file explorer."""
        source_path = Path(self.src_input.text()).expanduser().resolve()
        if source_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(source_path)))
        else:
            InfoBar.warning(
                title="Folder Not Found",
                content="The source folder doesn't exist.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
    
    def _open_destination_folder(self) -> None:
        """Open the destination folder in file explorer."""
        dest_path = Path(self.dst_input.text()).expanduser().resolve()
        if dest_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(dest_path)))
        else:
            InfoBar.warning(
                title="Folder Not Found",
                content="The destination folder doesn't exist.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
    
    def _save_recovery_backup_settings(self) -> None:
        """Save recovery backup settings"""
        self.config.set("enable_recovery_backup", self.enable_recovery_cb.isChecked(), persist=False)
        
        recovery_folder = self.recovery_folder_input.text().strip()
        if not recovery_folder:
            recovery_folder = str(Path.home() / "FileOrganizer_Recovery")
        
        self.config.set("recovery_backup_folder", recovery_folder, persist=False)
        
        # Save size limit with validation
        size_limit = self.backup_size_spin.value()
        available_space = self._get_available_space(Path(recovery_folder))
        
        if size_limit > available_space - 1.0:  # Leave 1GB buffer
            InfoBar.warning(
                title="Size Limit Warning",
                content=f"Size limit ({size_limit:.1f}GB) exceeds available space ({available_space:.1f}GB). Will use available space minus 1GB buffer.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=4000,
                parent=self._parent
            )
        
        self.config.set("recovery_backup_size_limit_gb", size_limit, persist=False)
        self.config.set("recovery_backup_retention_days", self.retention_spin.value(), persist=False)
    
    def _get_available_space(self, path: Path) -> float:
        """Get available disk space in GB for the given path.
        
        Args:
            path: Path to check (will use parent if path doesn't exist)
            
        Returns:
            Available space in GB
        """
        try:
            import shutil
            # Use parent directory if path doesn't exist yet
            check_path = path if path.exists() else path.parent
            stat = shutil.disk_usage(check_path)
            return stat.free / (1024 * 1024 * 1024)  # Convert bytes to GB
        except Exception:
            return 0.0  # Return 0 if check fails

    def _create_custom_categories_card(self) -> ThemedCardWidget:
        """Create card for managing custom file categories with modern design."""
        card, card_layout = self._create_card()

        # Header with title and add button
        header_layout = QHBoxLayout()
        header_layout.addWidget(BodyLabel("Custom Categories"))
        header_layout.addStretch()
        
        add_btn = PushButton(FIF.ADD, "Add Category")
        add_btn.setFixedSize(140, 32)
        add_btn.clicked.connect(self._add_custom_category)
        header_layout.addWidget(add_btn)
        
        card_layout.addLayout(header_layout)
        
        # Scroll area for category items
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)
        scroll.setMaximumHeight(400)
        scroll.setObjectName("categoriesScrollArea")
        
        # Apply transparent background to scroll area
        from qfluentwidgets import isDarkTheme
        scroll_bg = "transparent"
        scroll.setStyleSheet(f"""
            QScrollArea#categoriesScrollArea {{
                background-color: {scroll_bg};
                border: none;
            }}
        """)
        
        # Container for category cards
        self.categories_container = QWidget()
        self.categories_container.setObjectName("categoriesContainer")
        self.categories_layout = QVBoxLayout(self.categories_container)
        self.categories_layout.setContentsMargins(0, 8, 0, 8)
        self.categories_layout.setSpacing(8)
        
        # Set transparent background for container
        self.categories_container.setStyleSheet("QWidget#categoriesContainer { background-color: transparent; }")
        
        scroll.setWidget(self.categories_container)
        card_layout.addWidget(scroll, 1)
        
        self._refresh_custom_categories_list()

        return card

    def _refresh_custom_categories_list(self) -> None:
        """Refresh the category items with modern card design."""
        from qfluentwidgets import isDarkTheme
        
        # Clear existing items
        while self.categories_layout.count():
            item = self.categories_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        custom_cats = self.config.get_custom_categories()
        
        if not custom_cats:
            # Show empty state
            empty_widget = QWidget()
            empty_layout = QVBoxLayout(empty_widget)
            empty_layout.setContentsMargins(20, 40, 20, 40)
            empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            empty_label = BodyLabel("No custom categories yet")
            empty_label.setStyleSheet("color: rgb(153, 153, 153); font-size: 13px;")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(empty_label)
            
            hint_label = BodyLabel("Click 'Add Category' to create one")
            hint_label.setStyleSheet("color: rgb(128, 128, 128); font-size: 11px;")
            hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty_layout.addWidget(hint_label)
            
            self.categories_layout.addWidget(empty_widget)
        else:
            # Create a card for each category
            for name, extensions in custom_cats.items():
                self._create_category_item(name, extensions)
        
        self.categories_layout.addStretch()
    
    def _create_category_item(self, name: str, extensions: list) -> None:
        """Create a modern category item card with name, extensions, and remove button."""
        from qfluentwidgets import isDarkTheme, TransparentToolButton
        
        # Theme-aware colors
        is_dark = isDarkTheme()
        text_color = "rgb(230, 230, 230)" if is_dark else "rgb(30, 30, 30)"
        subtext_color = "rgb(176, 176, 176)" if is_dark else "rgb(153, 153, 153)"
        bg_color = "rgb(45, 46, 50)" if is_dark else "rgb(255, 255, 255)"
        border_color = "rgb(60, 63, 68)" if is_dark else "rgb(229, 231, 235)"
        hover_bg = "rgb(50, 51, 55)" if is_dark else "rgb(248, 249, 250)"
        
        # Item container
        item_widget = QWidget()
        item_widget.setFixedHeight(70)
        item_layout = QHBoxLayout(item_widget)
        item_layout.setContentsMargins(16, 12, 16, 12)
        item_layout.setSpacing(12)
        
        # Category name and extensions in vertical layout
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        text_layout.setContentsMargins(0, 0, 0, 0)
        
        category_name = BodyLabel(name)
        category_name.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {text_color};")
        text_layout.addWidget(category_name)
        
        # Extensions display
        exts_str = ", ".join(extensions)
        if len(exts_str) > 60:
            exts_str = exts_str[:60] + "..."
        extensions_label = BodyLabel(exts_str)
        extensions_label.setStyleSheet(f"font-size: 12px; color: {subtext_color};")
        text_layout.addWidget(extensions_label)
        
        item_layout.addLayout(text_layout, 1)
        
        # Extension count badge
        count_label = BodyLabel(f"{len(extensions)} ext")
        count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        count_label.setFixedSize(60, 24)
        count_label.setStyleSheet("""
            background-color: rgba(0, 159, 170, 0.15);
            color: rgb(0, 159, 170);
            border-radius: 12px;
            padding: 4px 8px;
            font-weight: 600;
            font-size: 11px;
        """)
        item_layout.addWidget(count_label)
        
        # Edit button
        edit_btn = TransparentToolButton(FIF.EDIT, self.categories_container)
        edit_btn.setFixedSize(36, 36)
        edit_btn.setToolTip(f"Edit '{name}'")
        edit_btn.installEventFilter(ToolTipFilter(edit_btn))
        edit_btn.setIconSize(QSize(16, 16))
        edit_btn.clicked.connect(lambda checked=False, n=name, e=extensions: self._edit_category(n, e))
        item_layout.addWidget(edit_btn)
        
        # Remove button using TransparentToolButton for better icon display
        remove_btn = TransparentToolButton(FIF.DELETE, self.categories_container)
        remove_btn.setFixedSize(36, 36)
        remove_btn.setToolTip(f"Remove '{name}'")
        remove_btn.installEventFilter(ToolTipFilter(remove_btn))
        remove_btn.setIconSize(QSize(16, 16))
        remove_btn.clicked.connect(lambda checked=False, n=name: self._remove_specific_category(n))
        item_layout.addWidget(remove_btn)
        
        # Apply card styling
        item_widget.setObjectName("categoryItemWidget")
        item_widget.setStyleSheet(f"""
            QWidget#categoryItemWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            QWidget#categoryItemWidget:hover {{
                background-color: {hover_bg};
                border: 1px solid {border_color};
            }}
        """)
        
        self.categories_layout.addWidget(item_widget)

    def _add_custom_category(self) -> None:
        """Prompt user to add a custom category"""
        # Create custom dialog for category name using MessageBox style
        name_dialog = MessageBox("Add Custom Category", "Enter the name for your custom category", self._parent)
        apply_message_box_theme(name_dialog)
        name_input = LineEdit()
        name_input.setPlaceholderText("e.g., E-Books, Music, Projects")
        name_dialog.textLayout.addWidget(name_input)
        name_dialog.yesButton.setText("Next")
        name_dialog.cancelButton.setText("Cancel")
        
        # Connect Enter key and set focus
        name_input.returnPressed.connect(name_dialog.accept)
        name_input.setFocus()
        
        if not name_dialog.exec():
            return
        
        name = name_input.text().strip()
        if not name:
            return

        # Create custom dialog for extensions using MessageBox style
        ext_dialog = MessageBox("Add Extensions", f"Enter file extensions for '{name}' (comma-separated)", self._parent)
        apply_message_box_theme(ext_dialog)
        ext_input = LineEdit()
        ext_input.setPlaceholderText("e.g., pdf, docx, txt")
        ext_dialog.textLayout.addWidget(ext_input)
        ext_dialog.yesButton.setText("Add")
        ext_dialog.cancelButton.setText("Cancel")
        
        # Connect Enter key and set focus
        ext_input.returnPressed.connect(ext_dialog.accept)
        ext_input.setFocus()
        
        if not ext_dialog.exec():
            return
        
        exts = ext_input.text().strip()
        if not exts:
            return
        
        extensions = [ext.strip().lstrip(".").lower() for ext in exts.split(",") if ext.strip()]
        if not extensions:
            w = MessageBox("Invalid Input", "No valid extensions provided.", self._parent)
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return
        
        # Check for spaces in extensions
        invalid_exts = [ext for ext in extensions if " " in ext]
        if invalid_exts:
            w = MessageBox(
                "Invalid Extensions", 
                f"Extensions cannot contain spaces: {', '.join(invalid_exts)}\n\nPlease use comma to separate extensions.",
                self._parent
            )
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return

        # Add to config
        self.config.add_custom_category(name, extensions)
        self._refresh_custom_categories_list()
        
        # Show success notification
        self._show_info_bar("Category Added", f"Added '{name}' with {len(extensions)} extension(s)")

    def _remove_specific_category(self, category_name: str) -> None:
        """Remove a specific custom category with confirmation."""
        # Confirm removal
        w = MessageBox("Confirm Removal", f"Remove custom category '{category_name}'?", self._parent)
        apply_message_box_theme(w)
        w.yesButton.setText("Yes")
        w.cancelButton.setText("No")
        
        if w.exec():
            self.config.remove_custom_category(category_name)
            self._refresh_custom_categories_list()
            self._show_info_bar("Category Removed", f"Removed '{category_name}'")

    def _edit_category(self, category_name: str, current_extensions: list) -> None:
        """Edit an existing custom category's name and extensions."""
        # Step 1: Edit category name
        name_dialog = MessageBox("Edit Category Name", "Edit the category name", self._parent)
        apply_message_box_theme(name_dialog)
        name_input = LineEdit()
        name_input.setPlaceholderText("e.g., E-Books, Music, Projects")
        name_input.setText(category_name)
        name_dialog.textLayout.addWidget(name_input)
        name_dialog.yesButton.setText("Next")
        name_dialog.cancelButton.setText("Cancel")
        
        # Connect Enter key and set focus
        name_input.returnPressed.connect(name_dialog.accept)
        name_input.setFocus()
        name_input.selectAll()  # Select all text for easy editing
        
        if not name_dialog.exec():
            return
        
        new_name = name_input.text().strip()
        if not new_name:
            return
        
        # Step 2: Edit extensions
        ext_dialog = MessageBox("Edit Extensions", f"Edit extensions for '{new_name}' (comma-separated)", self._parent)
        apply_message_box_theme(ext_dialog)
        ext_input = LineEdit()
        ext_input.setPlaceholderText("e.g., pdf, docx, txt")
        ext_input.setText(", ".join(current_extensions))
        ext_dialog.textLayout.addWidget(ext_input)
        ext_dialog.yesButton.setText("Save")
        ext_dialog.cancelButton.setText("Cancel")
        
        # Connect Enter key and set focus
        ext_input.returnPressed.connect(ext_dialog.accept)
        ext_input.setFocus()
        ext_input.selectAll()
        
        if not ext_dialog.exec():
            return
        
        exts = ext_input.text().strip()
        if not exts:
            w = MessageBox("Invalid Input", "Extensions cannot be empty.", self._parent)
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return
        
        extensions = [ext.strip().lstrip(".").lower() for ext in exts.split(",") if ext.strip()]
        if not extensions:
            w = MessageBox("Invalid Input", "No valid extensions provided.", self._parent)
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return
        
        # Check for spaces in extensions
        invalid_exts = [ext for ext in extensions if " " in ext]
        if invalid_exts:
            w = MessageBox(
                "Invalid Extensions", 
                f"Extensions cannot contain spaces: {', '.join(invalid_exts)}\n\nPlease use comma to separate extensions.",
                self._parent
            )
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            return
        
        # Update the category (remove old, add new)
        self.config.remove_custom_category(category_name)
        self.config.add_custom_category(new_name, extensions)
        self._refresh_custom_categories_list()
        
        # Show success notification
        if new_name != category_name:
            self._show_info_bar("Category Updated", f"Renamed to '{new_name}' with {len(extensions)} extension(s)")
        else:
            self._show_info_bar("Category Updated", f"Updated '{new_name}' with {len(extensions)} extension(s)")

    def _save_persistent_paths(self) -> None:
        """Save persistent folder paths to config"""
        src = (self.src_input.text() or "").strip()
        dst = (self.dst_input.text() or "").strip()
        auto_save = self.auto_save_cb.isChecked()
        
        self.config.set("last_source_folder", src)
        self.config.set("last_destination_folder", dst)
        self.config.set("auto_save_paths", auto_save)
    
    def _on_theme_changed(self, index: int) -> None:
        """Handle theme dropdown change"""
        # Call the parent's toggle theme method
        if self._parent:
            # Get current theme from parent
            current = self._parent.current_theme
            selected = Theme.LIGHT if index == 0 else Theme.DARK
            
            # Only toggle if different
            if current != selected:
                self._parent._toggle_theme()
    
    def _apply_all_settings(self) -> None:
        """Apply all settings changes at once"""
        try:
            # Save persistent paths
            self._save_persistent_paths()
            
            # Save duplicate handling
            self._save_duplicate_handling()
            
            # Save size filter settings
            self._save_size_filter_settings()
            
            # Save recovery backup settings
            self._save_recovery_backup_settings()
            
            # Save log export settings
            self._save_log_export_settings()
            
            # Save all changes at once
            self.config.save()
            
            # Show success message
            self._show_info_bar("Settings Saved", "All settings have been saved successfully!")
        except Exception as e:
            w = MessageBox("Error", f"Failed to save settings: {str(e)}", self._parent)
            apply_message_box_theme(w)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
    
    def apply_theme(self) -> None:
        """Apply theme-aware colors to caption labels"""
        # The gray caption labels need manual theme updates
        color = "rgb(153, 153, 153)" if not isDarkTheme() else "rgb(176, 176, 176)"
        if hasattr(self, 'content_widget') and self.content_widget is not None:
            apply_page_theme(self.content_widget, getattr(self, 'scroll_area', None))
        
        # Apply to recovery space label if it exists
        if hasattr(self, 'recovery_space_label'):
            self.recovery_space_label.setStyleSheet(f"color: {color};")
        
        # Apply to retention info label if it exists
        if hasattr(self, 'retention_info_label'):
            self.retention_info_label.setStyleSheet(f"color: {color};")


