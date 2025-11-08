"""Main application window with organize, framework, guide, and about pages."""
import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QMessageBox, QStackedWidget, QScrollArea, QTextBrowser, 
    QPlainTextEdit, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat

from qfluentwidgets import (
    PushButton, LineEdit, CheckBox, PlainTextEdit, CardWidget,
    BodyLabel, TitleLabel, setTheme, Theme, NavigationInterface,
    ProgressBar, IndeterminateProgressBar
)
from qfluentwidgets import FluentIcon as FIF

from app.core.file_organizer import FileOrganizer
from app.core.constants import FileCategory
from app.config.config_manager import ConfigManager
from app.services.logger_service import LoggerService


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


class OrganizeWorker(QThread):
    """Background worker for file organization with progress updates."""
    
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, organizer: FileOrganizer, source: Path, dest: Path, categories: list):
        """Initialize worker with organization parameters."""
        super().__init__()
        self.organizer = organizer
        self.source = source
        self.dest = dest
        self.categories = categories
    
    def run(self):
        """Run organization in background thread."""
        try:
            # Get file count first
            files = self.organizer.file_manager.get_files_in_folder(self.source)
            total_files = len(files)
            
            # Track progress
            self._setup_progress_tracking(total_files)
            
            # Perform organization
            stats = self.organizer.organize_folder(
                self.source,
                self.dest,
                self.categories
            )
            
            self.finished.emit(stats)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def _setup_progress_tracking(self, total_files: int):
        """Setup progress tracking by subscribing to logger."""
        self.current = 0
        self.total = total_files
        
        def track_progress(message: str):
            if "✓" in message or "→" in message:
                self.current += 1
                self.progress.emit(self.current, self.total)
        
        self.organizer.logger.subscribe(track_progress)


class OrganizePage:
    """File organization page with source/dest/category inputs and live log."""
    
    def __init__(
        self,
        on_organize,
        on_browse_source,
        on_browse_dest,
        on_clear_log,
        on_undo=None,
    ) -> None:
        """Initialize organize page with callbacks."""
        self.on_organize = on_organize
        self.on_browse_source = on_browse_source
        self.on_browse_dest = on_browse_dest
        self.on_clear_log = on_clear_log
        self.on_undo = on_undo or (lambda: None)

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
        layout.addWidget(self._create_progress_card())
        layout.addWidget(self._create_log_card())
        layout.addLayout(self._create_button_layout())
        layout.addStretch()

        scroll.setWidget(widget)
        self.root_widget = scroll
        return scroll

    def _create_source_card(self) -> CardWidget:
        """Create source folder selection card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(BodyLabel("Source Folder"))

        input_layout = QHBoxLayout()
        self.source_input = LineEdit()
        self.source_input.setPlaceholderText("Select source folder...")
        input_layout.addWidget(self.source_input, 1)

        browse_btn = PushButton("Browse")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.on_browse_source)
        input_layout.addWidget(browse_btn)

        layout.addLayout(input_layout)
        return card

    def _create_dest_card(self) -> CardWidget:
        """Create destination folder selection card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(BodyLabel("Destination Folder"))

        input_layout = QHBoxLayout()
        self.dest_input = LineEdit()
        self.dest_input.setPlaceholderText("Select destination folder...")
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

    def _create_progress_card(self) -> CardWidget:
        """Create progress bar card"""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label_layout = QHBoxLayout()
        label_layout.addWidget(BodyLabel("Progress"))
        self.progress_label = BodyLabel("Ready")
        label_layout.addStretch()
        label_layout.addWidget(self.progress_label)
        layout.addLayout(label_layout)

        self.progress_bar = ProgressBar()
        self.progress_bar.setMinimumHeight(8)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        return card

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
        """Create action button layout with Undo button"""
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.organize_btn = PushButton("Organize Files")
        self.organize_btn.setMinimumWidth(100)
        self.organize_btn.clicked.connect(self.on_organize)
        layout.addWidget(self.organize_btn)

        self.undo_btn = PushButton("Undo")
        self.undo_btn.setMinimumWidth(80)
        self.undo_btn.setEnabled(False)
        self.undo_btn.clicked.connect(self.on_undo)
        layout.addWidget(self.undo_btn)

        clear_btn = PushButton("Clear Log")
        clear_btn.setMinimumWidth(100)
        clear_btn.clicked.connect(self.on_clear_log)
        layout.addWidget(clear_btn)

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
        if hasattr(self, 'undo_btn') and enabled:
            # Only enable if there's something to undo
            pass
        elif hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(False)

    def update_progress(self, current: int, total: int) -> None:
        """Update progress bar and label"""
        if total > 0:
            percentage = int((current / total) * 100)
            self.progress_bar.setValue(percentage)
            self.progress_label.setText(f"{current}/{total} files")

    def show_progress(self, show: bool) -> None:
        """Show or hide progress bar"""
        self.progress_bar.setVisible(show)
        if not show:
            self.progress_bar.setValue(0)
            self.progress_label.setText("Ready")

    def get_source(self) -> str:
        """Get source folder path"""
        return self.source_input.text()

    def get_destination(self) -> str:
        """Get destination folder path"""
        return self.dest_input.text()

    def get_active_categories(self) -> list:
        """Get selected categories"""
        return [cat for cat, check in self.category_checks.items() if check.isChecked()]

    def append_log(self, message: str) -> None:
        """Append colored message to log"""
        self.log_text.append_colored(message)

    def clear_log(self) -> None:
        """Clear log display"""
        self.log_text.clear()


class InfoPageWithMarkdown:
    """Scrollable page with markdown content rendering."""
    
    def __init__(self, title: str, markdown_content: str) -> None:
        """Initialize info page."""
        self.title = title
        self.markdown_content = markdown_content

    def create(self) -> QWidget:
        """Create info page widget with markdown rendering"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        layout.addWidget(TitleLabel(self.title))

        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)

        text_browser = QTextBrowser()
        text_browser.setMarkdown(self.markdown_content)
        text_browser.setReadOnly(True)
        text_browser.setOpenExternalLinks(True)
        text_browser.document().setDocumentMargin(8)
        card_layout.addWidget(text_browser, 1)
        layout.addWidget(card, 1)

        scroll.setWidget(widget)
        return scroll


FRAMEWORK_MARKDOWN = """
# Jeff Su's Framework

## Folder Structure

- **01_Personal** — Personal files & hobbies
- **02_Work** — Work-related files
- **03_Templates** — Reusable templates
- **04_Temp_Share** — Temporary/shared files
- **05_Archive** — Old/archived files

## Principles

- Organize by **WHERE YOU USE** it (not where you found it)
- Keep files **searchable & descriptive**
- Limit folder depth to **5 levels**
- Use **consistent naming conventions**
- Archive outdated files **quarterly**

## CLI Compatible

- Works with PowerShell/bash tab completion
- No brackets in folder names
"""

GUIDE_MARKDOWN = """
# Smart File Naming

## Date-Based Naming
*For time-sensitive files*

- **2025_Budget** — Year only
- **2025-Q1_Analysis** — Year + Quarter
- **2025-05-15_Report_v1** — Full date format

**Best for:** Reports, meetings, invoices, receipts

## Alphabetical Naming
*For reference files*

- **ProjectName_Meeting_Notes** — Consistent keywords
- **Template_Invoice_2025** — Clear purpose
- **Guide_Setup_Instructions** — Self-documenting

**Best for:** Templates, guides, recurring documents, reference materials

## CLI Compatibility

**✓ GOOD** — `01_Personal` works with tab completion

**✗ BAD** — `[01] Personal` breaks PowerShell completion

**◐ OKAY** — `Personal_01` alternative format

**Recommendation:** Always use `01_Personal` format
"""

ABOUT_MARKDOWN = """
# File Organizer Pro

## Version 2.0.0

### Features

- **Automatic Organization** — Sort files by category
- **Jeff Su Framework** — Professional folder structure
- **Real-time Logging** — Live activity feedback
- **Modern UI** — Windows 11 Fluent Design
- **Persistent Settings** — Remember your preferences
- **Undo/Redo** — Rollback operations safely
- **Progress Tracking** — Real-time progress bar

### Architecture

- **Object-Oriented Design** (OOP)
- **SOLID Principles** — Clean code standards
- **Design Patterns** — Proven solutions
- **Type Hints** — Full static typing
- **Error Handling** — Comprehensive exception management

### Tech Stack

- **PyQt6** — Modern GUI framework
- **qfluentwidgets** — Fluent UI components
- **Python 3.9+** — Latest language features

### Status

✓ **Production-Ready**

Built with care for professional file management.

*Year: 2025*
"""


class FileOrganizerWindow(QMainWindow):
    """Main application window with navigation and page routing."""

    def __init__(
        self,
        file_organizer: FileOrganizer,
        config: ConfigManager,
        logger: LoggerService,
    ) -> None:
        """Initialize main window with dependency injection."""
        super().__init__()

        self.organizer = file_organizer
        self.config = config
        self.logger = logger
        self.worker = None

        setTheme(Theme.DARK)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Setup main UI structure"""
        self.setWindowTitle("File Organizer Pro")
        self.resize(1100, 700)
        self._center_window()

        self.stacked_widget = QStackedWidget()

        self.nav = NavigationInterface(self)
        self.nav.setCollapsible(True)
        self.nav.setExpandWidth(250)

        self.organize_page_obj = OrganizePage(
            on_organize=self._handle_organize,
            on_browse_source=self._browse_source,
            on_browse_dest=self._browse_dest,
            on_clear_log=self._clear_log,
            on_undo=self._handle_undo,
        )
        self.organize_page = self.organize_page_obj.create()

        framework_page = InfoPageWithMarkdown("Jeff Su's Framework", FRAMEWORK_MARKDOWN).create()
        guide_page = InfoPageWithMarkdown("Smart File Naming", GUIDE_MARKDOWN).create()
        about_page = InfoPageWithMarkdown("About File Organizer Pro", ABOUT_MARKDOWN).create()

        self.stacked_widget.addWidget(self.organize_page)
        self.nav.addItem(routeKey="organize", icon=FIF.FOLDER, text="Organize",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(0))

        self.stacked_widget.addWidget(framework_page)
        self.nav.addItem(routeKey="framework", icon=FIF.CHECKBOX, text="Framework",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(1))

        self.stacked_widget.addWidget(guide_page)
        self.nav.addItem(routeKey="guide", icon=FIF.INFO, text="Guide",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(2))

        self.stacked_widget.addWidget(about_page)
        self.nav.addItem(routeKey="about", icon=FIF.SETTING, text="About",
                        onClick=lambda: self.stacked_widget.setCurrentIndex(3))

        main_widget = QWidget()
        layout = QHBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.nav)
        layout.addWidget(self.stacked_widget, 1)
        self.setCentralWidget(main_widget)

        self.stacked_widget.setCurrentWidget(self.organize_page)

        self.logger.subscribe(self._on_log_message)

    def _center_window(self) -> None:
        """Center window on screen"""
        geometry = self.screen().availableGeometry()
        x = (geometry.width() - self.width()) // 2 + geometry.x()
        y = (geometry.height() - self.height()) // 2 + geometry.y()
        self.move(x, y)

    def _handle_organize(self) -> None:
        """Handle organize action with validation and background processing"""
        source = self.organize_page_obj.get_source()
        destination = self.organize_page_obj.get_destination()
        categories = self.organize_page_obj.get_active_categories()

        if not source or not Path(source).exists():
            QMessageBox.warning(self, "Error", "Invalid source folder")
            return
        if not destination:
            QMessageBox.warning(self, "Error", "Select destination folder")
            return
        if not categories:
            QMessageBox.warning(self, "Error", "Select at least one category")
            return

        # Disable buttons during processing
        self.organize_page_obj.set_buttons_enabled(False)
        self.organize_page_obj.show_progress(True)

        # Create and start worker thread
        self.worker = OrganizeWorker(
            self.organizer,
            Path(source),
            Path(destination),
            categories
        )
        
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_organize_finished)
        self.worker.error.connect(self._on_organize_error)
        self.worker.start()

    def _on_progress(self, current: int, total: int) -> None:
        """Handle progress updates"""
        self.organize_page_obj.update_progress(current, total)

    def _on_organize_finished(self, stats: dict) -> None:
        """Handle organization completion"""
        self.organize_page_obj.show_progress(False)
        self.organize_page_obj.set_buttons_enabled(True)
        
        # Enable undo button
        self.organize_page_obj.set_undo_enabled(
            self.organizer.history.can_undo()
        )
        
        QMessageBox.information(
            self, "Success",
            f"Organization Complete!\n\nMoved: {stats['moved']}\n"
            f"Errors: {stats['errors']}\nSkipped: {stats['skipped']}"
        )
        
        self.worker = None

    def _on_organize_error(self, error: str) -> None:
        """Handle organization error"""
        self.organize_page_obj.show_progress(False)
        self.organize_page_obj.set_buttons_enabled(True)
        QMessageBox.critical(self, "Error", f"Organization failed: {error}")
        self.worker = None

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
            self.config.set("destination_folder", folder)

    def _clear_log(self) -> None:
        """Clear log"""
        self.organize_page_obj.clear_log()

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
    
    file_service = FileService()
    file_manager = FileManager(logger)
    organizer = FileOrganizer(logger, file_service, file_manager)

    window = FileOrganizerWindow(organizer, config, logger)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
