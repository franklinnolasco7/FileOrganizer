"""Main application window with organize, changelogs, settings, and about pages."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QMessageBox, QStackedWidget, QScrollArea, QTextBrowser, 
    QPlainTextEdit, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QListWidget,
    QInputDialog, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QDragEnterEvent, QDropEvent

from qfluentwidgets import (
    PushButton, LineEdit, CheckBox, PlainTextEdit, CardWidget,
    BodyLabel, TitleLabel, setTheme, Theme, NavigationInterface, SpinBox, DoubleSpinBox
)
from qfluentwidgets import FluentIcon as FIF

from app.core.file_organizer import FileOrganizer
from app.core.constants import FileCategory, CUSTOM_CATEGORIES
from app.config.config_manager import ConfigManager
from app.services.logger_service import LoggerService
from app.core.file_manager import DuplicateHandlingStrategy


class DragDropLineEdit(LineEdit):
    """LineEdit with enhanced drag and drop support for folders."""
    
    def __init__(self, *args, **kwargs):
        """Initialize drag-drop enabled line edit."""
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self._is_dragging = False
        
        self._default_style = """
            QLineEdit {
                border: 2px solid transparent;
                border-radius: 6px;
                padding: 9px 12px;
                background-color: rgba(255, 255, 255, 0.05);
                font-size: 13px;
            }
            QLineEdit:hover {
                background-color: rgba(255, 255, 255, 0.08);
            }
            QLineEdit:focus {
                border: 2px solid #0078D4;
                background-color: rgba(255, 255, 255, 0.05);
            }
        """
        
        self._drag_style = """
            QLineEdit {
                border: 2px dashed #4CAF50;
                border-radius: 6px;
                padding: 9px 12px;
                background-color: rgba(76, 175, 80, 0.15);
                font-size: 13px;
            }
        """
        
        self._invalid_style = """
            QLineEdit {
                border: 2px dashed #F44336;
                border-radius: 6px;
                padding: 9px 12px;
                background-color: rgba(244, 67, 54, 0.15);
                font-size: 13px;
            }
        """
        
        self.setStyleSheet(self._default_style)
        self.setFixedHeight(38)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter with visual feedback."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                if path.is_dir():
                    event.acceptProposedAction()
                    self._is_dragging = True
                    self.setStyleSheet(self._drag_style)
                    self.setPlaceholderText("Drop folder here...")
                else:
                    event.ignore()
                    self._is_dragging = True
                    self.setStyleSheet(self._invalid_style)
                    self.setPlaceholderText("❌ Folders only")
            else:
                event.ignore()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event) -> None:
        """Handle drag move to maintain styling."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and Path(urls[0].toLocalFile()).is_dir():
                event.acceptProposedAction()
    
    def dragLeaveEvent(self, event) -> None:
        """Reset styling when drag leaves."""
        self._is_dragging = False
        self.setStyleSheet(self._default_style)
        self._reset_placeholder()
    
    def dropEvent(self, event) -> None:
        """Handle drop with validation and feedback."""
        self._is_dragging = False
        self.setStyleSheet(self._default_style)
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                folder_path = Path(urls[0].toLocalFile())
                if folder_path.is_dir():
                    self.setText(str(folder_path))
                    event.acceptProposedAction()
                    self._reset_placeholder()
                    
                    self.setStyleSheet("""
                        QLineEdit {
                            border: 2px solid #4CAF50;
                            border-radius: 6px;
                            padding: 9px 12px;
                            background-color: rgba(76, 175, 80, 0.2);
                            font-size: 13px;
                        }
                    """)
                    
                    QTimer.singleShot(500, lambda: self.setStyleSheet(self._default_style))
                else:
                    event.ignore()
                    self._reset_placeholder()
        else:
            event.ignore()
            self._reset_placeholder()
    
    def _reset_placeholder(self) -> None:
        """Reset placeholder to original text."""
        if not self.text():
            if hasattr(self, 'objectName') and 'source' in self.objectName().lower():
                self.setPlaceholderText("Select or drag source folder...")
            else:
                self.setPlaceholderText("Select or drag destination folder...")


class ColoredPlainTextEdit(PlainTextEdit):
    """Custom text edit with color-coded log levels."""
    
    COLORS = {
        "INFO": QColor("#B0B0B0"),
        "SUCCESS": QColor("#4CAF50"),
        "WARNING": QColor("#FF9800"),
        "ERROR": QColor("#F44336"),
        "DEBUG": QColor("#757575"),
    }
    
    def __init__(self) -> None:
        """Initialize colored text edit"""
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setMaximumBlockCount(500)
    
    def append_colored(self, message: str) -> None:
        """Append message with color based on log level."""
        level = self._extract_level(message)
        formatted_msg = self._strip_timestamp(message)
        
        self.blockSignals(True)
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(self.COLORS.get(level, self.COLORS["INFO"]))
        if level == "ERROR":
            fmt.setFontWeight(700)
        
        cursor.insertText(formatted_msg + "\n", fmt)
        self.setTextCursor(cursor)
        
        self.blockSignals(False)
        self.ensureCursorVisible()
    
    @staticmethod
    def _strip_timestamp(message: str) -> str:
        """Remove first timestamp bracket; keep [LEVEL] and message."""
        try:
            first_bracket = message.find("]")
            if first_bracket != -1:
                remainder = message[first_bracket+1:].strip()
                return remainder
        except Exception:
            pass
        return message
    
    @staticmethod
    def _extract_level(message: str) -> str:
        """Extract log level from message."""
        levels = ["ERROR", "WARNING", "SUCCESS", "DEBUG", "INFO"]
        for level in levels:
            if f"[{level}]" in message:
                return level
        return "INFO"


class PreviewDialog(QDialog):
    """Dialog showing file organization preview."""
    
    def __init__(self, preview_data: dict, parent=None):
        """Initialize preview dialog with file data."""
        super().__init__(parent)
        self.setWindowTitle("File Organization Preview")
        self.resize(900, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title_text = f"Found {preview_data['total']} files to organize"
        if preview_data.get('skipped_by_size', 0) > 0:
            title_text += f" ({preview_data['skipped_by_size']} skipped by size filter)"
        title = TitleLabel(title_text)
        layout.addWidget(title)
        
        # Category summary
        if preview_data['summary']:
            summary_card = self._create_summary_card(preview_data['summary'])
            layout.addWidget(summary_card)
        
        # File list table
        if preview_data['files']:
            layout.addWidget(BodyLabel("File Details:"))
            table = self._create_file_table(preview_data['files'])
            layout.addWidget(table, 1)
        
        # Close button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        close_btn = PushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def _create_summary_card(self, summary: dict) -> CardWidget:
        """Create summary card with category counts."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(8)
        
        card_layout.addWidget(BodyLabel("Files per Category:"))
        
        # Create grid layout for categories
        grid_layout = QHBoxLayout()
        for category, count in summary.items():
            cat_label = BodyLabel(f"📁 {category}: {count}")
            cat_label.setStyleSheet("font-weight: 500;")
            grid_layout.addWidget(cat_label)
        
        grid_layout.addStretch()
        card_layout.addLayout(grid_layout)
        
        return card
    
    def _create_file_table(self, files: list) -> QTableWidget:
        """Create table showing files and their destinations."""
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["File Name", "Size (KB)", "Current Location", "Destination Category"])
        table.setRowCount(len(files))
        
        for row, file_info in enumerate(files):
            # File name
            name_item = QTableWidgetItem(file_info['name'])
            table.setItem(row, 0, name_item)
            
            # File size
            size_kb = file_info.get('size_kb', 0)
            size_item = QTableWidgetItem(f"{size_kb:.2f}")
            table.setItem(row, 1, size_item)
            
            # Current location
            current_item = QTableWidgetItem(file_info['current'])
            table.setItem(row, 2, current_item)
            
            # Category
            cat_item = QTableWidgetItem(file_info['category'])
            table.setItem(row, 3, cat_item)
        
        # Resize columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        
        return table


class SettingsPage:
    """Settings panel for user preferences and custom categories"""
    
    def __init__(self, config: ConfigManager, on_close) -> None:
        """Initialize settings page
        
        Args:
            config: Configuration manager
            on_close: Close callback function
        """
        self.config = config
        self.on_close = on_close
    
    def create(self) -> QWidget:
        """Create settings page widget
        
        Returns:
            Settings page widget
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("Settings"))
        
        layout.addWidget(self._create_persistent_paths_card())
        layout.addWidget(self._create_duplicate_handling_card())
        layout.addWidget(self._create_size_filter_settings_card())
        layout.addWidget(self._create_log_export_card())
        layout.addWidget(self._create_custom_categories_card())
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll

    def _create_persistent_paths_card(self) -> CardWidget:
        """Create card for persistent folder path settings."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(BodyLabel("Persistent Paths"))
        
        src_layout = QHBoxLayout()
        src_label = BodyLabel("Last Source Folder")
        self.src_input = LineEdit()
        self.src_input.setPlaceholderText("Enter last used source path")
        self.src_input.setText(self.config.get("last_source_folder", ""))
        src_layout.addWidget(src_label)
        src_layout.addWidget(self.src_input, 1)
        card_layout.addLayout(src_layout)
        
        dst_layout = QHBoxLayout()
        dst_label = BodyLabel("Last Destination Folder")
        self.dst_input = LineEdit()
        self.dst_input.setPlaceholderText("Enter last used destination path")
        self.dst_input.setText(self.config.get("last_destination_folder", ""))
        dst_layout.addWidget(dst_label)
        dst_layout.addWidget(self.dst_input, 1)
        card_layout.addLayout(dst_layout)
        
        self.auto_save_cb = CheckBox("Auto-save on change (auto-fill paths on startup)")
        self.auto_save_cb.setChecked(self.config.get("auto_save_paths", True))
        card_layout.addWidget(self.auto_save_cb)
        
        btn_layout = QHBoxLayout()
        save_btn = PushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save_persistent_paths)
        btn_layout.addWidget(save_btn)
        
        close_btn = PushButton("Close")
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self.on_close)
        btn_layout.addWidget(close_btn)
        
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)
        
        return card

    def _create_duplicate_handling_card(self) -> CardWidget:
        """Create card for duplicate file handling settings."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(BodyLabel("Duplicate File Handling"))
        
        # Radio buttons for duplicate strategy
        self.duplicate_group = QButtonGroup()
        
        self.rename_radio = QRadioButton("Rename duplicates (file_1.txt, file_2.txt)")
        self.skip_radio = QRadioButton("Skip duplicates (keep existing)")
        self.replace_radio = QRadioButton("Replace duplicates (overwrite existing)")
        
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
        
        # Save button
        save_btn = PushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save_duplicate_handling)
        card_layout.addWidget(save_btn)
        
        return card

    def _save_duplicate_handling(self) -> None:
        """Save duplicate handling preference."""
        if self.rename_radio.isChecked():
            strategy = "rename"
        elif self.skip_radio.isChecked():
            strategy = "skip"
        elif self.replace_radio.isChecked():
            strategy = "replace"
        else:
            strategy = "rename"
        
        self.config.set("duplicate_handling", strategy)
        QMessageBox.information(None, "Saved", f"Duplicate handling set to: {strategy}")

    def _create_size_filter_settings_card(self) -> CardWidget:
        """Create card for file size filter default settings."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(BodyLabel("File Size Filter Defaults"))
        
        # Enable filter checkbox
        self.settings_enable_filter = CheckBox("Enable size filter by default")
        self.settings_enable_filter.setChecked(self.config.get("enable_size_filter", False))
        card_layout.addWidget(self.settings_enable_filter)
        
        # Min size setting
        min_layout = QHBoxLayout()
        min_label = BodyLabel("Default Minimum Size (KB):")
        min_label.setMinimumWidth(200)
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
        max_label = BodyLabel("Default Maximum Size (KB):")
        max_label.setMinimumWidth(200)
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
        
        # Save button
        save_btn = PushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save_size_filter_settings)
        card_layout.addWidget(save_btn)
        
        return card
    
    def _save_size_filter_settings(self) -> None:
        """Save file size filter settings."""
        enable_filter = self.settings_enable_filter.isChecked()
        min_size = self.settings_min_size.value()
        max_size = self.settings_max_size.value()
        
        self.config.set("enable_size_filter", enable_filter)
        self.config.set("min_file_size_kb", min_size)
        self.config.set("max_file_size_kb", max_size)
        
        QMessageBox.information(None, "Saved", "File size filter settings saved successfully!")

    def _create_log_export_card(self) -> CardWidget:
        """Create card for activity log export directory settings."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(BodyLabel("Activity Log Export"))
        
        # Export directory setting
        dir_layout = QHBoxLayout()
        dir_label = BodyLabel("Default Export Directory:")
        dir_label.setMinimumWidth(200)
        self.log_export_dir_input = LineEdit()
        self.log_export_dir_input.setPlaceholderText("Select directory for log exports")
        self.log_export_dir_input.setText(self.config.get("log_export_directory", str(Path.home())))
        dir_layout.addWidget(dir_label)
        dir_layout.addWidget(self.log_export_dir_input, 1)
        
        browse_btn = PushButton("Browse")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self._browse_log_export_dir)
        dir_layout.addWidget(browse_btn)
        card_layout.addLayout(dir_layout)
        
        # Save button
        save_btn = PushButton("Save")
        save_btn.setMinimumWidth(100)
        save_btn.clicked.connect(self._save_log_export_settings)
        card_layout.addWidget(save_btn)
        
        return card
    
    def _browse_log_export_dir(self) -> None:
        """Browse for log export directory."""
        folder = QFileDialog.getExistingDirectory(None, "Select Log Export Directory")
        if folder:
            self.log_export_dir_input.setText(folder)
    
    def _save_log_export_settings(self) -> None:
        """Save log export directory settings."""
        export_dir = self.log_export_dir_input.text().strip()
        
        if export_dir and not Path(export_dir).exists():
            QMessageBox.warning(None, "Invalid Directory", "The specified directory does not exist.")
            return
        
        if not export_dir:
            export_dir = str(Path.home())
        
        self.config.set("log_export_directory", export_dir)
        QMessageBox.information(None, "Saved", "Log export directory saved successfully!")

    def _create_custom_categories_card(self) -> CardWidget:
        """Create card for managing custom file categories."""
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)

        card_layout.addWidget(BodyLabel("Custom Categories"))

        # List widget to show categories and their extensions
        self.categories_list = QListWidget()
        self._refresh_custom_categories_list()
        card_layout.addWidget(self.categories_list, 1)

        btn_layout = QHBoxLayout()

        add_btn = PushButton("Add Category")
        add_btn.setMinimumWidth(120)
        add_btn.clicked.connect(self._add_custom_category)
        btn_layout.addWidget(add_btn)

        remove_btn = PushButton("Remove Selected")
        remove_btn.setMinimumWidth(120)
        remove_btn.clicked.connect(self._remove_custom_category)
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        card_layout.addLayout(btn_layout)

        return card

    def _refresh_custom_categories_list(self) -> None:
        """Refresh the list widget with current categories and extensions."""
        self.categories_list.clear()
        custom_cats = self.config.get_custom_categories()
        for name, extensions in custom_cats.items():
            exts_str = ", ".join(extensions)
            self.categories_list.addItem(f"{name}: {exts_str}")

    def _add_custom_category(self) -> None:
        """Prompt user to add a custom category"""
        # Get category name
        name, ok = QInputDialog.getText(None, "Add Custom Category", "Category Name:")
        if not ok or not name.strip():
            return
        name = name.strip()

        # Get extensions comma-separated
        exts, ok = QInputDialog.getText(None, "Add Extensions",
                                       "List extensions separated by commas (e.g. pdf,docx,txt):")
        if not ok or not exts.strip():
            return
        
        extensions = [ext.strip().lstrip(".").lower() for ext in exts.split(",") if ext.strip()]
        if not extensions:
            QMessageBox.warning(None, "Invalid Input", "No valid extensions provided.")
            return

        # Add to config
        self.config.add_custom_category(name, extensions)
        self._refresh_custom_categories_list()

    def _remove_custom_category(self) -> None:
        """Remove selected custom category"""
        selected = self.categories_list.selectedItems()
        if not selected:
            QMessageBox.warning(None, "Remove Category", "Select a category to remove.")
            return
        
        item_text = selected[0].text()
        # Extract category name before ":"
        category_name = item_text.split(":", 1)[0].strip()
        
        reply = QMessageBox.question(None, "Confirm Removal",
                                     f"Remove custom category '{category_name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.config.remove_custom_category(category_name)
            self._refresh_custom_categories_list()

    def _save_persistent_paths(self) -> None:
        """Save persistent folder paths to config"""
        src = (self.src_input.text() or "").strip()
        dst = (self.dst_input.text() or "").strip()
        auto_save = self.auto_save_cb.isChecked()
        
        self.config.set("last_source_folder", src)
        self.config.set("last_destination_folder", dst)
        self.config.set("auto_save_paths", auto_save)
        
        QMessageBox.information(None, "Saved", "Settings saved successfully!")


class ChangelogsPage:
    """Changelogs page showing version history"""
    
    def __init__(self) -> None:
        """Initialize changelogs page"""
        pass
    
    def create(self) -> QWidget:
        """Create changelogs page widget
        
        Returns:
            Changelogs page widget
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        
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
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        
        # Version header
        version_layout = QHBoxLayout()
        version_label = TitleLabel(f"v{version}")
        date_label = BodyLabel(date)
        date_label.setStyleSheet("color: #999999; font-size: 11px;")
        version_layout.addWidget(version_label)
        version_layout.addStretch()
        version_layout.addWidget(date_label)
        card_layout.addLayout(version_layout)
        
        # Changes list
        for change in changes:
            card_layout.addWidget(BodyLabel(f"• {change}"))
        
        return card


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

    def create(self) -> QWidget:
        """Create organize page widget"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

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
        return scroll

    def _create_source_card(self) -> CardWidget:
        """Create source folder selection card with drag-drop support"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label_layout = QHBoxLayout()
        label_layout.addWidget(BodyLabel("Source Folder"))
        
        hint_label = BodyLabel("📁 Drag & drop supported")
        hint_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: 500;")
        label_layout.addStretch()
        label_layout.addWidget(hint_label)
        layout.addLayout(label_layout)

        input_layout = QHBoxLayout()
        self.source_input = DragDropLineEdit()
        self.source_input.setObjectName("source_input")
        self.source_input.setPlaceholderText("Select or drag source folder...")
        input_layout.addWidget(self.source_input, 1)

        browse_btn = PushButton("Browse")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.on_browse_source)
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        return card

    def _create_dest_card(self) -> CardWidget:
        """Create destination folder selection card with drag-drop support"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label_layout = QHBoxLayout()
        label_layout.addWidget(BodyLabel("Destination Folder"))
        
        hint_label = BodyLabel("📁 Drag & drop supported")
        hint_label.setStyleSheet("color: #4CAF50; font-size: 11px; font-weight: 500;")
        label_layout.addStretch()
        label_layout.addWidget(hint_label)
        layout.addLayout(label_layout)

        input_layout = QHBoxLayout()
        self.dest_input = DragDropLineEdit()
        self.dest_input.setObjectName("dest_input")
        self.dest_input.setPlaceholderText("Select or drag destination folder...")
        input_layout.addWidget(self.dest_input, 1)

        browse_btn = PushButton("Browse")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.on_browse_dest)
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        return card

    def _create_category_card(self) -> CardWidget:
        """Create file category selection card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(BodyLabel("File Categories"))

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
    
    def _create_size_filter_card(self) -> CardWidget:
        """Create file size filter card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
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
        max_layout.addWidget(self.max_size_input)
        size_layout.addLayout(max_layout)
        
        size_layout.addStretch()
        layout.addLayout(size_layout)
        
        return card
    
    def _toggle_size_filter(self, enabled: bool) -> None:
        """Enable/disable size filter inputs"""
        self.min_size_input.setEnabled(enabled)
        self.max_size_input.setEnabled(enabled)

    def _create_log_card(self) -> CardWidget:
        """Create activity log card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(BodyLabel("Activity Log"))

        self.log_text = ColoredPlainTextEdit()
        layout.addWidget(self.log_text, 1)

        return card

    def _create_button_layout(self) -> QHBoxLayout:
        """Create action button layout"""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        # Preview button
        preview_btn = PushButton("Preview")
        preview_btn.setMinimumWidth(80)
        preview_btn.clicked.connect(self.on_preview)
        layout.addWidget(preview_btn)

        # Organize button
        self.organize_btn = PushButton("Organize Files")
        self.organize_btn.setMinimumWidth(120)
        self.organize_btn.clicked.connect(self.on_organize)
        layout.addWidget(self.organize_btn)

        # Undo button
        self.undo_btn = PushButton("Undo")
        self.undo_btn.setMinimumWidth(80)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.on_undo)
        layout.addWidget(self.undo_btn)

        # Clear Log button
        clear_btn = PushButton("Clear Log")
        clear_btn.setMinimumWidth(100)
        clear_btn.clicked.connect(self.on_clear_log)
        layout.addWidget(clear_btn)
        
        # Export Log button
        export_btn = PushButton("Export Log")
        export_btn.setMinimumWidth(100)
        export_btn.clicked.connect(self.on_export_log)
        layout.addWidget(export_btn)

        layout.addStretch()
        return layout

    def set_undo_enabled(self, enabled: bool) -> None:
        """Enable or disable undo button"""
        if hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(enabled)

    def set_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable organize and undo buttons during processing"""
        if hasattr(self, 'organize_btn'):
            self.organize_btn.setEnabled(enabled)

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


class AboutPage:
    """About page with project information and credits"""
    
    def __init__(self) -> None:
        """Initialize about page"""
        pass
    
    def create(self) -> QWidget:
        """Create about page widget
        
        Returns:
            About page widget
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)
        
        layout.addWidget(TitleLabel("About"))
        
        # App Info Card
        layout.addWidget(self._create_app_info_card())
        
        # Credits Card
        layout.addWidget(self._create_credits_card())
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        return scroll
    
    def _create_app_info_card(self) -> CardWidget:
        """Create app information card
        
        Returns:
            App info card widget
        """
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        
        # Title
        card_layout.addWidget(TitleLabel("File Organizer"))
        
        # Version
        version_layout = QHBoxLayout()
        version_label = BodyLabel("Version:")
        version_label.setStyleSheet("font-weight: 500;")
        version_value = BodyLabel("2.7.1")
        version_layout.addWidget(version_label)
        version_layout.addWidget(version_value)
        version_layout.addStretch()
        card_layout.addLayout(version_layout)
        
        # Release Date
        date_layout = QHBoxLayout()
        date_label = BodyLabel("Release Date:")
        date_label.setStyleSheet("font-weight: 500;")
        date_value = BodyLabel("November 2025")
        date_layout.addWidget(date_label)
        date_layout.addWidget(date_value)
        date_layout.addStretch()
        card_layout.addLayout(date_layout)
        
        # Description
        description = BodyLabel("An open source project for organizing files by category. Helps you keep your files organized and easy to find.")
        description.setWordWrap(True)
        card_layout.addWidget(description)
        
        # GitHub Link
        github_layout = QHBoxLayout()
        github_label = BodyLabel("Repository:")
        github_label.setStyleSheet("font-weight: 500;")
        github_link = BodyLabel("https://github.com/franklinnolasco7/FileOrganizer")
        github_link.setStyleSheet("color: #0078D4; text-decoration: underline;")
        github_layout.addWidget(github_label)
        github_layout.addWidget(github_link)
        github_layout.addStretch()
        card_layout.addLayout(github_layout)
        
        return card
    
    def _create_credits_card(self) -> CardWidget:
        """Create credits card
        
        Returns:
            Credits card widget
        """
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(TitleLabel("Credits"))
        
        # Developer
        dev_layout = QHBoxLayout()
        dev_label = BodyLabel("Developer:")
        dev_label.setStyleSheet("font-weight: 500;")
        dev_name = BodyLabel("Franklin Nolasco")
        dev_layout.addWidget(dev_label)
        dev_layout.addWidget(dev_name)
        dev_layout.addStretch()
        card_layout.addLayout(dev_layout)
        
        # Framework
        framework_layout = QHBoxLayout()
        framework_label = BodyLabel("Framework:")
        framework_label.setStyleSheet("font-weight: 500;")
        framework_value = BodyLabel("PyQt6")
        framework_layout.addWidget(framework_label)
        framework_layout.addWidget(framework_value)
        framework_layout.addStretch()
        card_layout.addLayout(framework_layout)
        
        # UI Theme
        theme_layout = QHBoxLayout()
        theme_label = BodyLabel("UI Theme:")
        theme_label.setStyleSheet("font-weight: 500;")
        theme_value = BodyLabel("qfluentwidgets")
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_value)
        theme_layout.addStretch()
        card_layout.addLayout(theme_layout)
        
        # Type
        type_layout = QHBoxLayout()
        type_label = BodyLabel("Type:")
        type_label.setStyleSheet("font-weight: 500;")
        type_value = BodyLabel("Open Source")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_value)
        type_layout.addStretch()
        card_layout.addLayout(type_layout)
        
        return card


class FileOrganizerWindow(QMainWindow):
    """Main application window with navigation and page routing"""

    def __init__(
        self,
        file_organizer: FileOrganizer,
        config: ConfigManager,
        logger: LoggerService,
    ) -> None:
        """Initialize main window
        
        Args:
            file_organizer: File organizer instance
            config: Configuration manager
            logger: Logger service
        """
        super().__init__()

        self.organizer = file_organizer
        self.config = config
        self.logger = logger

        setTheme(Theme.DARK)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup main UI structure"""
        self.setWindowTitle("File Organizer")
        self.resize(1100, 700)
        self._center_window()

        self.stacked_widget = QStackedWidget()

        self.nav = NavigationInterface(self)
        self.nav.setCollapsible(True)
        self.nav.setExpandWidth(250)

        # Create Organize Page
        self.organize_page_obj = OrganizePage(
            on_organize=self._handle_organize,
            on_browse_source=self._browse_source,
            on_browse_dest=self._browse_dest,
            on_clear_log=self._clear_log,
            on_undo=self._handle_undo,
            on_preview=self._handle_preview,
            on_export_log=self._export_log,
        )
        self.organize_page = self.organize_page_obj.create()

        # Create Changelogs Page
        changelogs_page = ChangelogsPage().create()

        # Create Settings Page
        self.settings_page_obj = SettingsPage(self.config, on_close=self._return_to_organize)
        self.settings_page = self.settings_page_obj.create()

        # Create About Page
        about_page = AboutPage().create()

        # Add all pages to stack widget
        self.stacked_widget.addWidget(self.organize_page)  # Index 0
        self.stacked_widget.addWidget(changelogs_page)  # Index 1
        self.stacked_widget.addWidget(self.settings_page)  # Index 2
        self.stacked_widget.addWidget(about_page)  # Index 3

        # Add navigation items
        self.nav.addItem(routeKey="organize", icon=FIF.FOLDER, text="Organize",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(0))

        self.nav.addItem(routeKey="changelogs", icon=FIF.HISTORY, text="Changelogs",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(1))

        self.nav.addItem(routeKey="settings", icon=FIF.SETTING, text="Settings",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(2))

        self.nav.addItem(routeKey="about", icon=FIF.INFO, text="About",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(3))

        # Setup main layout
        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav)
        layout.addWidget(self.stacked_widget, 1)
        self.setCentralWidget(main_widget)

        # Set initial page
        self.stacked_widget.setCurrentWidget(self.organize_page)

        # Load saved settings on startup
        self._apply_saved_settings()

        # Subscribe to logger
        self.logger.subscribe(self._on_log_message)

    def _center_window(self) -> None:
        """Center window on screen"""
        geometry = self.screen().availableGeometry()
        x = (geometry.width() - self.width()) // 2 + geometry.x()
        y = (geometry.height() - self.height()) // 2 + geometry.y()
        self.move(x, y)

    def _apply_saved_settings(self) -> None:
        """Load saved settings from config and apply to organize page."""
        auto_save_enabled = self.config.get("auto_save_paths", True)
        
        if auto_save_enabled:
            src = self.config.get("last_source_folder", "")
            dst = self.config.get("last_destination_folder", "")
            if src:
                self.organize_page_obj.source_input.setText(src)
            if dst:
                self.organize_page_obj.dest_input.setText(dst)
            
            # Load size filter settings
            enable_filter = self.config.get("enable_size_filter", False)
            min_size = self.config.get("min_file_size_kb", 0)
            max_size = self.config.get("max_file_size_kb", 0)
            
            self.organize_page_obj.enable_size_filter_check.setChecked(enable_filter)
            self.organize_page_obj.min_size_input.setValue(min_size)
            self.organize_page_obj.max_size_input.setValue(max_size)

    def _return_to_organize(self) -> None:
        """Return from settings to organize page."""
        self.stacked_widget.setCurrentWidget(self.organize_page)

    def _handle_preview(self) -> None:
        """Show preview of files to be organized."""
        source = self.organize_page_obj.get_source()
        destination = self.organize_page_obj.get_destination()
        categories = self.organize_page_obj.get_active_categories()
        size_filter = self.organize_page_obj.get_size_filter_settings()

        if not source or not Path(source).exists():
            QMessageBox.warning(self, "Error", "Invalid source folder")
            return
        if not destination:
            QMessageBox.warning(self, "Error", "Select destination folder")
            return
        if not categories:
            QMessageBox.warning(self, "Error", "Select at least one category")
            return

        try:
            preview_data = self.organizer.preview_organization(
                Path(source),
                Path(destination),
                categories,
                min_size_kb=size_filter['min_size_kb'],
                max_size_kb=size_filter['max_size_kb'],
                enable_size_filter=size_filter['enabled']
            )

            if preview_data['total'] == 0:
                msg = "No files found to organize"
                if size_filter['enabled'] and preview_data.get('skipped_by_size', 0) > 0:
                    msg += f"\n({preview_data['skipped_by_size']} files skipped by size filter)"
                QMessageBox.information(self, "Preview", msg)
                return

            dialog = PreviewDialog(preview_data, self)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Preview failed: {str(e)}")

    def _handle_organize(self) -> None:
        """Handle organize action with validation"""
        source = self.organize_page_obj.get_source()
        destination = self.organize_page_obj.get_destination()
        categories = self.organize_page_obj.get_active_categories()
        size_filter = self.organize_page_obj.get_size_filter_settings()

        if not source or not Path(source).exists():
            QMessageBox.warning(self, "Error", "Invalid source folder")
            return
        if not destination:
            QMessageBox.warning(self, "Error", "Select destination folder")
            return
        if not categories:
            QMessageBox.warning(self, "Error", "Select at least one category")
            return

        try:
            self.organize_page_obj.set_buttons_enabled(False)
            
            stats = self.organizer.organize_folder(
                Path(source),
                Path(destination),
                categories,
                min_size_kb=size_filter['min_size_kb'],
                max_size_kb=size_filter['max_size_kb'],
                enable_size_filter=size_filter['enabled']
            )
            
            self.organize_page_obj.set_undo_enabled(
                self.organizer.history.can_undo()
            )
            
            # Auto-persist the paths used for this organization if auto-save enabled
            auto_save_enabled = self.config.get("auto_save_paths", True)
            if auto_save_enabled:
                self.config.set("last_source_folder", source)
                self.config.set("last_destination_folder", destination)
                
                # Save size filter settings
                self.config.set("enable_size_filter", size_filter['enabled'])
                self.config.set("min_file_size_kb", size_filter['min_size_kb'])
                self.config.set("max_file_size_kb", size_filter['max_size_kb'])
            
            QMessageBox.information(
                self, "Success",
                f"Organization Complete!\n\nMoved: {stats['moved']}\n"
                f"Errors: {stats['errors']}\nSkipped: {stats['skipped']}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Organization failed: {str(e)}")
        finally:
            self.organize_page_obj.set_buttons_enabled(True)

    def _handle_undo(self) -> None:
        """Handle undo action with confirmation"""
        if not self.organizer.history.can_undo():
            QMessageBox.warning(self, "Undo", "No operations to undo")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Undo",
            "Are you sure you want to undo the last organization?\n"
            "Files will be moved back to their original locations.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                stats = self.organizer.undo_last_operation()
                
                self.organize_page_obj.set_undo_enabled(
                    self.organizer.history.can_undo()
                )
                
                QMessageBox.information(
                    self, "Undo Complete",
                    f"Successfully restored {stats['restored']} files!\n"
                    f"Errors: {stats['errors']}\n"
                    f"Folders removed: {stats.get('folders_removed', 0)}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Undo Failed", f"Undo operation failed: {str(e)}")

    def _browse_source(self) -> None:
        """Browse source folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.organize_page_obj.source_input.setText(folder)

    def _browse_dest(self) -> None:
        """Browse destination folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.organize_page_obj.dest_input.setText(folder)

    def _clear_log(self) -> None:
        """Clear log"""
        self.organize_page_obj.clear_log()
    
    def _export_log(self) -> None:
        """Export activity log to timestamped text file"""
        log_content = self.organize_page_obj.get_log_content()
        
        if not log_content.strip():
            QMessageBox.information(self, "Export Log", "Activity log is empty. Nothing to export.")
            return
        
        # Generate timestamped filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"FileOrganizer_Log_{timestamp}.txt"
        
        # Get export directory from config
        export_dir = self.config.get("log_export_directory", str(Path.home()))
        default_path = Path(export_dir) / default_filename
        
        # Open save file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Activity Log",
            str(default_path),
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"File Organizer Activity Log\n")
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(log_content)
                
                QMessageBox.information(self, "Export Successful", f"Activity log exported to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export log:\n{str(e)}")

    def _on_log_message(self, message: str) -> None:
        """Handle log message from logger"""
        self.organize_page_obj.append_log(message)


def main() -> None:
    """Application entry point"""
    from app.config.config_manager import DEFAULT_CONFIG_SCHEMA
    from app.services.file_service import FileService
    from app.core.file_manager import FileManager

    app = QApplication(sys.argv)

    logger = LoggerService(max_history=1000)
    
    config_file = Path.home() / ".file_organizer_config.json"
    config = ConfigManager(config_file, DEFAULT_CONFIG_SCHEMA)
    
    # Get duplicate handling strategy from config
    strategy_str = config.get("duplicate_handling", "rename")
    strategy_map = {
        "skip": DuplicateHandlingStrategy.SKIP,
        "rename": DuplicateHandlingStrategy.RENAME,
        "replace": DuplicateHandlingStrategy.REPLACE,
    }
    duplicate_strategy = strategy_map.get(strategy_str, DuplicateHandlingStrategy.RENAME)
    
    file_service = FileService()
    file_manager = FileManager(logger, duplicate_strategy=duplicate_strategy)
    organizer = FileOrganizer(logger, file_service, file_manager)

    window = FileOrganizerWindow(organizer, config, logger)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
