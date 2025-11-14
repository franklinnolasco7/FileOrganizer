"""Main application window with organize, changelogs, settings, and about pages."""
import sys
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QApplication, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QMessageBox, QStackedWidget, QScrollArea, QTextBrowser, 
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, QProcess, QUrl, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QDragEnterEvent, QDropEvent, QDesktopServices, QIcon

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit, CheckBox, PlainTextEdit, CardWidget,
    BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel, setTheme, Theme, 
    NavigationInterface, SpinBox, DoubleSpinBox, NavigationItemPosition, SmoothScrollArea, 
    InfoBar, InfoBarPosition, ToolTipFilter, isDarkTheme, setCustomStyleSheet, ListWidget, 
    RadioButton, HyperlinkLabel, MessageBox, Dialog, ComboBox, FluentWindow, qconfig, toggleTheme
)
from qfluentwidgets import FluentIcon as FIF

from app.core.file_organizer import FileOrganizer
from app.core.constants import FileCategory, CUSTOM_CATEGORIES
from app.config.config_manager import ConfigManager
from app.services.logger_service import LoggerService
from app.core.file_manager import DuplicateHandlingStrategy


from app.ui.widgets import DragDropLineEdit, ColoredPlainTextEdit, PreviewDialog
from app.ui.pages import SettingsPage, ChangelogsPage, OrganizePage, AboutPage
from app.ui.theme_utils import apply_page_theme, apply_message_box_theme, get_brand_icon

class FileOrganizerWindow(FluentWindow):
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
        
        # Safety flags to prevent concurrent operations
        self.is_organizing = False
        self.is_previewing = False

        # Store current theme (already set in main())
        saved_theme = self.config.get("theme", "dark")
        self.current_theme = Theme.LIGHT if saved_theme == "light" else Theme.DARK
        
        # Set FluentWindow properties with larger size
        self.brand_icon = get_brand_icon()
        self.setWindowIcon(self.brand_icon)
        self.setWindowTitle("File Organizer")
        self.resize(1400, 850)  # Increased from 1100x700
        
        self._setup_ui()
        
        # Connect to theme change signal for proper updates
        qconfig.themeChanged.connect(self._on_theme_changed)

    def _show_info_bar(self, title: str, content: str, position=InfoBarPosition.TOP, error: bool = False) -> None:
        """Helper method to show InfoBar with consistent styling
        
        Args:
            title: InfoBar title
            content: InfoBar content message
            position: Position of the InfoBar (default: TOP)
            error: If True, shows error InfoBar; otherwise shows success InfoBar
        """
        info_bar_func = InfoBar.error if error else InfoBar.success
        info_bar_func(
            title=title,
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=position,
            duration=3000,
            parent=self
        )

    def _setup_ui(self) -> None:
        """Setup main UI structure"""
        self._center_window()

        # Create all pages first
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
        self.organize_page.setObjectName("organizePage")

        # Create Changelogs Page
        self.changelogs_page_obj = ChangelogsPage()
        changelogs_page = self.changelogs_page_obj.create()
        changelogs_page.setObjectName("changelogsPage")

        # Create Settings Page
        self.settings_page_obj = SettingsPage(self.config, on_close=self._return_to_organize, parent=self)
        self.settings_page = self.settings_page_obj.create()
        self.settings_page.setObjectName("settingsPage")

        # Create About Page
        self.about_page_obj = AboutPage(parent=self)
        about_page = self.about_page_obj.create()
        about_page.setObjectName("aboutPage")

        # Add navigation items using FluentWindow's interface
        self.addSubInterface(self.organize_page, FIF.FOLDER, "Organize", NavigationItemPosition.TOP)
        self.addSubInterface(changelogs_page, FIF.HISTORY, "Changelogs", NavigationItemPosition.TOP)
        self.addSubInterface(about_page, FIF.INFO, "About", NavigationItemPosition.TOP)
        self.addSubInterface(self.settings_page, FIF.SETTING, "Settings", NavigationItemPosition.BOTTOM)

        # Load saved settings on startup
        self._apply_saved_settings()

        # Subscribe to logger
        self.logger.subscribe(self._on_log_message)
        
        # Apply initial theme to sublabels
        self.organize_page_obj.apply_hint_label_theme()
        self.changelogs_page_obj.apply_date_label_theme()
        
        # Apply theme to settings page caption labels
        if hasattr(self.settings_page_obj, 'apply_theme'):
            self.settings_page_obj.apply_theme()
        
        # Apply theme to cards after UI is fully loaded
        QTimer.singleShot(100, self._apply_theme_to_cards)
        
        # Connect source input changes to update button states
        self.organize_page_obj.source_input.textChanged.connect(self._update_button_states)
        
        # Set initial button states
        self._update_button_states()

    def _on_page_changed(self, index):
        """Handle page change in stacked widget"""
        pass

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
        self.switchTo(self.organize_page)

    def _on_theme_changed(self, theme: Theme) -> None:
        """Handle theme changes from qconfig"""
        # Update all CardWidget backgrounds manually since they don't auto-update
        self._apply_theme_to_cards()
        
        # Update custom labels that need manual theme updates
        if hasattr(self, 'organize_page_obj'):
            self.organize_page_obj.apply_hint_label_theme()
        
        if hasattr(self, 'changelogs_page_obj'):
            self.changelogs_page_obj.apply_date_label_theme()
        
        # Apply theme to settings page
        if hasattr(self, 'settings_page_obj'):
            # Refresh custom categories styling
            if hasattr(self.settings_page_obj, 'categories_layout'):
                self.settings_page_obj._refresh_custom_categories_list()
            # Apply theme to caption labels
            if hasattr(self.settings_page_obj, 'apply_theme'):
                self.settings_page_obj.apply_theme()
        
        # Apply shared page backgrounds
        for page_obj in [
            getattr(self, 'organize_page_obj', None),
            getattr(self, 'settings_page_obj', None),
            getattr(self, 'about_page_obj', None),
            getattr(self, 'changelogs_page_obj', None),
        ]:
            if page_obj and getattr(page_obj, 'content_widget', None) is not None:
                apply_page_theme(page_obj.content_widget, getattr(page_obj, 'scroll_area', None))

        # Update log colors if log widget exists
        if hasattr(self, 'organize_page_obj') and hasattr(self.organize_page_obj, 'log_text'):
            self.organize_page_obj.log_text._update_colors()
    
    def _apply_theme_to_cards(self) -> None:
        """Apply theme colors to all CardWidgets"""
        # Find all CardWidget instances and update their stylesheets
        for page in [self.organize_page, self.settings_page]:
            if page:
                cards = page.findChildren(CardWidget)
                for card in cards:
                    # Force CardWidget to update by clearing and reapplying its stylesheet
                    card.setStyleSheet(card.styleSheet())

    def _toggle_theme(self) -> None:
        """Toggle between light and dark theme"""
        # Use QFluentWidgets' built-in toggleTheme() function
        # This properly switches between light/dark and emits themeChanged signal
        toggleTheme()
        
        # Update our local theme reference
        self.current_theme = qconfig.theme
        theme_name = "light" if self.current_theme == Theme.LIGHT else "dark"
        
        # Save preference to config
        self.config.set("theme", theme_name)
        
        # Show notification
        self._show_info_bar("Theme Changed", f"Switched to {theme_name.capitalize()} Mode")

    def _handle_preview(self) -> None:
        """Show preview of files to be organized."""
        # Prevent concurrent operations
        if self.is_organizing:
            self._show_info_bar("Organization in Progress", "Please wait for the current organization to complete", InfoBarPosition.TOP)
            return
        
        if self.is_previewing:
            self._show_info_bar("Preview in Progress", "Please wait for the current preview to complete", InfoBarPosition.TOP)
            return
        
        source = self.organize_page_obj.get_source()
        destination = self.organize_page_obj.get_destination()
        categories = self.organize_page_obj.get_active_categories()
        size_filter = self.organize_page_obj.get_size_filter_settings()

        if not source or not Path(source).exists():
            self._show_info_bar("Invalid Source", "Please select a valid source folder", InfoBarPosition.TOP, error=True)
            return
        if not destination:
            self._show_info_bar("No Destination", "Please select a destination folder", InfoBarPosition.TOP, error=True)
            return
        if not categories:
            self._show_info_bar("No Categories", "Please select at least one category", InfoBarPosition.TOP, error=True)
            return
        
        # Validate source and destination are not the same
        try:
            source_resolved = Path(source).resolve()
            dest_resolved = Path(destination).resolve()
            if source_resolved == dest_resolved:
                self._show_info_bar("Invalid Folders", "Source and destination folders cannot be the same", InfoBarPosition.TOP, error=True)
                return
        except Exception:
            pass  # If resolution fails, let the organizer handle it

        try:
            self.is_previewing = True
            self.organize_page_obj.set_buttons_enabled(False)
            
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
                    msg += f" ({preview_data['skipped_by_size']} files skipped by size filter)"
                self._show_info_bar("No Files", msg, InfoBarPosition.TOP)
                return

            dialog = PreviewDialog(preview_data, self)
            dialog.exec()

        except Exception as e:
            self._show_info_bar("Preview Failed", str(e), InfoBarPosition.TOP, error=True)
        finally:
            self.is_previewing = False
            self.organize_page_obj.set_buttons_enabled(True)

    def _handle_organize(self) -> None:
        """Handle organize action with validation"""
        # Prevent concurrent operations
        if self.is_organizing:
            self._show_info_bar("Operation in Progress", "Please wait for the current organization to complete", InfoBarPosition.TOP)
            return
        
        if self.is_previewing:
            self._show_info_bar("Preview in Progress", "Please wait for the preview to complete", InfoBarPosition.TOP)
            return
        
        source = self.organize_page_obj.get_source()
        destination = self.organize_page_obj.get_destination()
        categories = self.organize_page_obj.get_active_categories()
        size_filter = self.organize_page_obj.get_size_filter_settings()

        if not source or not Path(source).exists():
            self._show_info_bar("Invalid Source", "Please select a valid source folder", InfoBarPosition.TOP, error=True)
            return
        if not destination:
            self._show_info_bar("No Destination", "Please select a destination folder", InfoBarPosition.TOP, error=True)
            return
        if not categories:
            self._show_info_bar("No Categories", "Please select at least one category", InfoBarPosition.TOP, error=True)
            return
        
        # Validate source and destination are not the same
        try:
            source_resolved = Path(source).resolve()
            dest_resolved = Path(destination).resolve()
            if source_resolved == dest_resolved:
                self._show_info_bar("Invalid Folders", "Source and destination folders cannot be the same", InfoBarPosition.TOP, error=True)
                return
            # Check if destination is inside source (would cause recursive issues)
            if dest_resolved.is_relative_to(source_resolved):
                self._show_info_bar("Invalid Folders", "Destination folder cannot be inside source folder", InfoBarPosition.TOP, error=True)
                return
        except Exception:
            pass  # If resolution fails, let the organizer handle it

        try:
            # Set organizing flag FIRST to prevent concurrent clicks
            self.is_organizing = True
            self.organize_page_obj.set_buttons_enabled(False)
            
            stats = self.organizer.organize_folder(
                Path(source),
                Path(destination),
                categories,
                min_size_kb=size_filter['min_size_kb'],
                max_size_kb=size_filter['max_size_kb'],
                enable_size_filter=size_filter['enabled']
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
            
            # Show results based on what happened
            if stats['moved'] == 0 and stats['errors'] == 0 and stats['skipped'] > 0:
                # No files were moved, only skipped (possibly already organized)
                self._show_info_bar("No Files Organized", f"{stats['skipped']} files were skipped (no matching files or already organized)", InfoBarPosition.TOP)
            elif stats['moved'] == 0 and stats['errors'] == 0 and stats['skipped'] == 0:
                # Nothing happened at all
                self._show_info_bar("No Files Found", "No files found to organize in the source folder", InfoBarPosition.TOP)
            else:
                # Show success dialog with stats
                recovery_folder = self.config.get("recovery_backup_folder", str(Path.home() / "FileOrganizer_Recovery"))
                w = MessageBox(
                    "Success",
                    f"Organization Complete!\n\n"
                    f"Moved: {stats['moved']}\n"
                    f"Errors: {stats['errors']}\n"
                    f"Skipped: {stats['skipped']}\n\n"
                    f"Recovery backup saved to:\n{recovery_folder}",
                    self
                )
                apply_message_box_theme(w)
                w.cancelButton.hide()
                w.yesButton.setText("OK")
                w.exec()
            
            # Update undo button state AFTER checking results
            # This ensures undo button reflects actual undoable operations
            self._update_button_states()
        except Exception as e:
            self._show_info_bar("Organization Failed", str(e), InfoBarPosition.TOP, error=True)
        finally:
            self.is_organizing = False
            self.organize_page_obj.set_buttons_enabled(True)

    def _handle_undo(self) -> None:
        """Handle undo action with confirmation"""
        # Prevent undo during organize or preview operations
        if self.is_organizing:
            self._show_info_bar("Organization in Progress", "Please wait for the current organization to complete", InfoBarPosition.TOP)
            return
        
        if self.is_previewing:
            self._show_info_bar("Preview in Progress", "Please wait for the preview to complete", InfoBarPosition.TOP)
            return
        
        # Double-check if undo is available
        if not self.organizer.history.can_undo():
            self._show_info_bar("Nothing to Undo", "No operations available to undo", InfoBarPosition.TOP)
            # Ensure button is disabled
            self.organize_page_obj.set_undo_enabled(False)
            return
        
        w = MessageBox(
            "Confirm Undo",
            "Are you sure you want to undo the last organization?\n"
            "Files will be moved back to their original locations.",
            self
        )
        apply_message_box_theme(w)
        w.yesButton.setText("Yes")
        w.cancelButton.setText("No")
        
        if w.exec():
            try:
                stats = self.organizer.undo_last_operation()
                
                # Update button states immediately after undo completes
                self._update_button_states()
                
                # Show success with stats in InfoBar
                self._show_info_bar(
                    "Undo Complete",
                    f"Restored {stats['restored']} files • {stats['errors']} errors • {stats.get('folders_removed', 0)} folders removed",
                    InfoBarPosition.TOP
                )
            except Exception as e:
                self._show_info_bar("Undo Failed", str(e), InfoBarPosition.TOP, error=True)
                # Update button states even on error
                self._update_button_states()

    def _update_button_states(self) -> None:
        """Update organize, preview, and undo button states based on current conditions"""
        has_source = bool(self.organize_page_obj.get_source().strip())
        can_undo = self.organizer.history.can_undo()
        
        # Organize and Preview buttons: enabled only when source folder is selected
        self.organize_page_obj.organize_btn.setEnabled(has_source)
        self.organize_page_obj.preview_btn.setEnabled(has_source)
        
        # Undo button: enabled only when there's history
        self.organize_page_obj.undo_btn.setEnabled(can_undo)
    
    def _browse_source(self) -> None:
        """Browse source folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder")
        if folder:
            self.organize_page_obj.source_input.setText(folder)
            self._update_button_states()

    def _browse_dest(self) -> None:
        """Browse destination folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if folder:
            self.organize_page_obj.dest_input.setText(folder)

    def _clear_log(self) -> None:
        """Clear log"""
        log_content = self.organize_page_obj.get_log_content()
        
        if not log_content.strip():
            self._show_info_bar("Log Empty", "Activity log is already empty", InfoBarPosition.TOP)
            return
        
        self.organize_page_obj.clear_log()
        
        # Show success notification
        self._show_info_bar("Log Cleared", "Activity log has been cleared")
    
    def _export_log(self) -> None:
        """Export activity log to timestamped text file"""
        log_content = self.organize_page_obj.get_log_content()
        
        if not log_content.strip():
            self._show_info_bar("Log Empty", "Activity log is empty. Nothing to export", InfoBarPosition.TOP)
            return
        
        # Clean up separator lines from log content
        lines = log_content.split('\n')
        # Remove empty lines from export (they were just for spacing in the app)
        cleaned_lines = [line for line in lines if line.strip()]
        log_content = '\n'.join(cleaned_lines)
        
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
                    f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(log_content)
                
                # Get just the filename for cleaner message
                filename = Path(file_path).name
                self._show_info_bar("Export Successful", f"Log exported as {filename}", InfoBarPosition.TOP)
            except Exception as e:
                self._show_info_bar("Export Failed", f"Failed to export: {str(e)}", InfoBarPosition.TOP, error=True)

    def _on_log_message(self, message: str) -> None:
        """Handle log message from logger"""
        self.organize_page_obj.append_log(message)


def main() -> None:
    """Application entry point"""
    import sys
    from pathlib import Path
    from PyQt6.QtWidgets import QApplication
    
    # Create QApplication FIRST
    app = QApplication(sys.argv)
    app.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
    app.setWindowIcon(get_brand_icon())
    
    # NOW import everything else
    from app.config.config_manager import DEFAULT_CONFIG_SCHEMA, ConfigManager
    from app.services.file_service import FileService
    from app.core.file_manager import FileManager, DuplicateHandlingStrategy
    from app.core.file_organizer import FileOrganizer
    from app.services.logger_service import LoggerService
    from qfluentwidgets import Theme, setTheme

    logger = LoggerService(max_history=1000)
    
    config_file = Path.home() / ".file_organizer_config.json"
    config = ConfigManager(config_file, DEFAULT_CONFIG_SCHEMA)
    
    # Set theme BEFORE creating window using setTheme() as documented
    saved_theme = config.get("theme", "dark")
    theme = Theme.LIGHT if saved_theme == "light" else Theme.DARK
    setTheme(theme)
    
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
    organizer = FileOrganizer(logger, file_service, file_manager, config)

    window = FileOrganizerWindow(organizer, config, logger)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
