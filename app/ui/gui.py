"""Main application window with organize, changelogs, settings, and about pages."""
import sys
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QFileDialog, QMessageBox, QStackedWidget, QScrollArea, QTextBrowser, 
    QPlainTextEdit, QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QInputDialog, QButtonGroup
)
from PyQt6.QtCore import Qt, QTimer, QProcess, QUrl, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QTextCursor, QColor, QTextCharFormat, QDragEnterEvent, QDropEvent, QDesktopServices

from qfluentwidgets import (
    PushButton, PrimaryPushButton, LineEdit, CheckBox, PlainTextEdit, CardWidget,
    BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel, CaptionLabel, setTheme, Theme, 
    NavigationInterface, SpinBox, DoubleSpinBox, NavigationItemPosition, SmoothScrollArea, 
    InfoBar, InfoBarPosition, ToolTipFilter, isDarkTheme, setCustomStyleSheet, ListWidget, 
    RadioButton, HyperlinkLabel, MessageBox, Dialog, ComboBox
)
from qfluentwidgets import FluentIcon as FIF

from app.core.file_organizer import FileOrganizer
from app.core.constants import FileCategory, CUSTOM_CATEGORIES
from app.config.config_manager import ConfigManager
from app.services.logger_service import LoggerService
from app.core.file_manager import DuplicateHandlingStrategy


from app.ui.widgets import DragDropLineEdit, ColoredPlainTextEdit, PreviewDialog
from app.ui.pages import SettingsPage, RecoveryManagerPage, ChangelogsPage, OrganizePage, AboutPage

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
        
        # Safety flags to prevent concurrent operations
        self.is_organizing = False
        self.is_previewing = False

        # Store current theme (already set in main())
        saved_theme = self.config.get("theme", "dark")
        self.current_theme = Theme.LIGHT if saved_theme == "light" else Theme.DARK
        
        self._setup_ui()
        
        # Apply window background theme after UI is setup
        self._apply_window_theme()
        
        # Force widget updates to ensure theme colors apply properly
        QApplication.processEvents()
        self.update()
        self.repaint()

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

        # Create Recovery Manager Page
        self.recovery_page_obj = RecoveryManagerPage(self.config, self.logger, parent=self)
        self.recovery_page = self.recovery_page_obj.create()

        # Create Changelogs Page
        self.changelogs_page_obj = ChangelogsPage()
        changelogs_page = self.changelogs_page_obj.create()

        # Create Settings Page
        self.settings_page_obj = SettingsPage(self.config, on_close=self._return_to_organize, parent=self)
        self.settings_page = self.settings_page_obj.create()

        # Create About Page
        self.about_page_obj = AboutPage(parent=self)
        about_page = self.about_page_obj.create()

        # Add all pages to stack widget
        self.stacked_widget.addWidget(self.organize_page)
        self.stacked_widget.addWidget(self.recovery_page)
        self.stacked_widget.addWidget(changelogs_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(about_page)

        # Add navigation items
        nav_items = [
            {
                "routeKey": "organize",
                "icon": FIF.FOLDER,
                "text": "Organize",
                "onClick": lambda: self.stacked_widget.setCurrentIndex(0),
                "tooltip": "Organize your files into categories"
            },
            {
                "routeKey": "recovery",
                "icon": FIF.SYNC,
                "text": "Recovery",
                "onClick": lambda: self.stacked_widget.setCurrentIndex(1),
                "tooltip": "View and restore from backups"
            },
            {
                "routeKey": "changelogs",
                "icon": FIF.HISTORY,
                "text": "Changelogs",
                "onClick": lambda: self.stacked_widget.setCurrentIndex(2),
                "tooltip": "View version history and updates"
            },
            {
                "routeKey": "about",
                "icon": FIF.INFO,
                "text": "About",
                "onClick": lambda: self.stacked_widget.setCurrentIndex(4),
                "tooltip": "About this application"
            }
        ]
        
        # Add main navigation items
        for item in nav_items:
            self.nav.addItem(
                routeKey=item["routeKey"],
                icon=item["icon"],
                text=item["text"],
                onClick=item["onClick"],
                tooltip=item["tooltip"]
            )
        
        # Add bottom navigation items
        bottom_items = [
            {
                "routeKey": "settings",
                "icon": FIF.SETTING,
                "text": "Settings",
                "onClick": lambda: self.stacked_widget.setCurrentIndex(3),
                "tooltip": "Configure application settings"
            }
        ]
        
        for item in bottom_items:
            self.nav.addItem(
                routeKey=item["routeKey"],
                icon=item["icon"],
                text=item["text"],
                onClick=item["onClick"],
                position=NavigationItemPosition.BOTTOM,
                tooltip=item["tooltip"]
            )

        # Setup main layout
        main_widget = QWidget()
        main_widget.setObjectName("centralWidget")
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
        
        # Apply initial theme to sublabels
        self.organize_page_obj.apply_hint_label_theme()
        self.changelogs_page_obj.apply_date_label_theme()
        
        # Connect source input changes to update button states
        self.organize_page_obj.source_input.textChanged.connect(self._update_button_states)
        
        # Set initial button states
        self._update_button_states()
        
        # Force update all pages to ensure proper theme rendering
        for i in range(self.stacked_widget.count()):
            page = self.stacked_widget.widget(i)
            if page:
                page.update()

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

    def _apply_window_theme(self) -> None:
        """Apply theme-aware background color to the main window and content areas"""
        # Improved color palette for better UI/UX with enhanced contrast
        if self.current_theme == Theme.LIGHT:
            # Light mode: Better contrast for visible borders and outlines
            main_bg = "rgb(243, 244, 246)"        # Light gray background
            page_bg = "rgb(250, 250, 251)"        # Slightly off-white for content
            nav_bg = "rgb(248, 249, 250)"         # Very subtle gray for navigation
            border_color = "rgb(229, 231, 235)"   # Visible border color
            card_bg = "rgb(255, 255, 255)"        # Pure white for cards to stand out
            card_hover_bg = "rgb(245, 246, 247)"  # More noticeable hover - medium gray
            shadow = "rgba(0, 0, 0, 0.05)"        # Subtle shadow for depth
        else:
            # Dark mode: Comfortable dark grays
            main_bg = "rgb(32, 33, 36)"           # Modern dark gray
            page_bg = "rgb(32, 33, 36)"           # Same as main for consistency
            nav_bg = "rgb(45, 46, 49)"            # Slightly lighter for navigation
            border_color = "rgb(60, 63, 68)"      # Dark mode border
            card_bg = "rgb(38, 39, 43)"           # Slightly lighter for cards
            card_hover_bg = "rgb(48, 49, 53)"     # More noticeable hover - lighter
            shadow = "rgba(0, 0, 0, 0.3)"         # Stronger shadow in dark mode
        
        # Apply comprehensive styling for smooth theme experience
        self.setStyleSheet(f"""
            /* Main window background */
            QMainWindow {{
                background-color: {main_bg};
            }}
            
            /* Central widget (contains nav + content) */
            QWidget#centralWidget {{
                background-color: {main_bg};
            }}
            
            /* Content area */
            QStackedWidget {{
                background-color: {page_bg};
                border-radius: 0px;
            }}
            
            /* Smooth scroll areas */
            SmoothScrollArea {{
                background-color: {page_bg};
                border: none;
            }}
            
            QWidget#pageScrollArea {{
                background-color: {page_bg};
                border: none;
            }}
            
            QWidget#pageContentWidget {{
                background-color: {page_bg};
            }}
            
            /* Enhanced card styling for better visibility */
            CardWidget {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
            
            CardWidget:hover {{
                background-color: {card_hover_bg};
                border: 1px solid {border_color};
            }}
            
            /* Activity log text area - clearly visible border */
            ColoredPlainTextEdit, PlainTextEdit#activityLogTextEdit {{
                background-color: {card_bg};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px;
            }}
            
            /* Line edits - subtle borders */
            LineEdit {{
                border: 1px solid {border_color};
            }}
            
            /* List widgets - visible borders */
            ListWidget {{
                border: 1px solid {border_color};
                background-color: {card_bg};
            }}
            
            /* Dialog windows - theme-aware popups */
            QDialog, QMessageBox, QInputDialog {{
                background-color: {card_bg};
            }}
            
            QMessageBox QLabel {{
                color: {"rgb(30, 30, 30)" if self.current_theme == Theme.LIGHT else "rgb(230, 230, 230)"};
                background-color: transparent;
            }}
            
            QInputDialog QLabel {{
                color: {"rgb(30, 30, 30)" if self.current_theme == Theme.LIGHT else "rgb(230, 230, 230)"};
                background-color: transparent;
            }}
            
            QInputDialog QLineEdit {{
                background-color: {page_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px;
                color: {"rgb(30, 30, 30)" if self.current_theme == Theme.LIGHT else "rgb(230, 230, 230)"};
            }}
            
            /* Dialog buttons - QPushButton styling */
            QDialog QPushButton, QMessageBox QPushButton, QInputDialog QPushButton {{
                background-color: {page_bg};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 6px 16px;
                color: {"rgb(30, 30, 30)" if self.current_theme == Theme.LIGHT else "rgb(230, 230, 230)"};
                min-width: 70px;
            }}
            
            QDialog QPushButton:hover, QMessageBox QPushButton:hover, QInputDialog QPushButton:hover {{
                background-color: {"rgb(240, 241, 243)" if self.current_theme == Theme.LIGHT else "rgb(48, 49, 53)"};
                border: 1px solid {"rgb(200, 201, 205)" if self.current_theme == Theme.LIGHT else "rgb(70, 73, 78)"};
            }}
            
            QDialog QPushButton:pressed, QMessageBox QPushButton:pressed, QInputDialog QPushButton:pressed {{
                background-color: {"rgb(230, 231, 233)" if self.current_theme == Theme.LIGHT else "rgb(58, 59, 63)"};
            }}
            
            /* Default/Primary button styling - matches qfluentwidgets accent color */
            /* Using cyan to match CheckBox checkmarks and PrimaryPushButton */
            QDialog QPushButton:default, QMessageBox QPushButton:default {{
                background-color: rgb(0, 159, 170);
                color: rgb(255, 255, 255);
                border: 1px solid rgb(0, 159, 170);
                font-weight: 500;
            }}
            
            QDialog QPushButton:default:hover, QMessageBox QPushButton:default:hover {{
                background-color: {"rgb(0, 139, 150)" if self.current_theme == Theme.LIGHT else "rgb(26, 173, 184)"};
            }}
            
            QDialog QPushButton:default:pressed, QMessageBox QPushButton:default:pressed {{
                background-color: {"rgb(0, 119, 130)" if self.current_theme == Theme.LIGHT else "rgb(0, 139, 150)"};
            }}
        """)

    def _toggle_theme(self) -> None:
        """Toggle between light and dark theme"""
        # Toggle theme
        if self.current_theme == Theme.DARK:
            self.current_theme = Theme.LIGHT
            theme_name = "light"
        else:
            self.current_theme = Theme.DARK
            theme_name = "dark"
        
        # Apply theme to all qfluentwidgets components
        # save=False because we manage our own config, lazy=False for immediate update
        setTheme(self.current_theme, save=False, lazy=False)
        
        # Apply window background color
        self._apply_window_theme()
        
        # Force complete widget tree update
        self.update()
        self.repaint()
        if hasattr(self, 'nav'):
            self.nav.update()
        if hasattr(self, 'stacked_widget'):
            self.stacked_widget.update()
        
        # Update log colors if log widget exists
        if hasattr(self, 'organize_page_obj') and hasattr(self.organize_page_obj, 'log_text'):
            self.organize_page_obj.log_text._update_colors()
        
        # Update hint labels in organize page
        if hasattr(self, 'organize_page_obj'):
            self.organize_page_obj.apply_hint_label_theme()
        
        # Update date labels in changelogs page
        if hasattr(self, 'changelogs_page_obj'):
            self.changelogs_page_obj.apply_date_label_theme()
        
        # Refresh custom categories styling if settings page exists
        if hasattr(self, 'settings_page_obj') and hasattr(self.settings_page_obj, 'categories_layout'):
            self.settings_page_obj._refresh_custom_categories_list()
        
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
        cleaned_lines = [line for line in lines if not line.strip().startswith('═')]
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
    
    # NOW import everything else
    from app.config.config_manager import DEFAULT_CONFIG_SCHEMA, ConfigManager
    from app.services.file_service import FileService
    from app.core.file_manager import FileManager, DuplicateHandlingStrategy
    from app.core.file_organizer import FileOrganizer
    from app.services.logger_service import LoggerService
    from qfluentwidgets import setTheme, Theme

    logger = LoggerService(max_history=1000)
    
    config_file = Path.home() / ".file_organizer_config.json"
    config = ConfigManager(config_file, DEFAULT_CONFIG_SCHEMA)
    
    # Set theme BEFORE creating window
    saved_theme = config.get("theme", "dark")
    theme = Theme.LIGHT if saved_theme == "light" else Theme.DARK
    # save=False because we manage config ourselves, lazy=False for immediate effect
    setTheme(theme, save=False, lazy=False)
    
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
