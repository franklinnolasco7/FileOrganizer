"""Recovery manager page for viewing and restoring from backups."""
from pathlib import Path
from typing import List
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QScrollArea
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from qfluentwidgets import (
    PushButton, PrimaryPushButton, CardWidget,
    BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel,
    InfoBar, InfoBarPosition, ToolTipFilter, isDarkTheme,
    MessageBox, ComboBox, CheckBox, ListWidget, qconfig
)
from qfluentwidgets import FluentIcon as FIF

from app.config.config_manager import ConfigManager
from app.services.logger_service import LoggerService


class RecoveryManagerPage:
    """Recovery manager page for viewing and restoring from backups."""
    
    def __init__(self, config: ConfigManager, logger: LoggerService, parent=None) -> None:
        """Initialize recovery manager page.
        
        Args:
            config: Configuration manager
            logger: Logger service
            parent: Parent widget for dialogs
        """
        self.config = config
        self.logger = logger
        self._parent = parent
        
        from app.core.recovery_manager import RecoveryManager
        recovery_folder = Path(config.get("recovery_backup_folder", str(Path.home() / "FileOrganizer_Recovery")))
        self.recovery_manager = RecoveryManager(logger, recovery_folder)
        
        self.current_backup = None
        self.file_checkboxes = []
    
    def create(self) -> QWidget:
        """Create recovery manager page widget.
        
        Returns:
            Recovery manager page widget
        """
        # Main container
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(16, 24, 16, 24)
        main_layout.setSpacing(20)
        
        # Title
        main_layout.addWidget(TitleLabel("Recovery Manager"))
        
        # Split layout: backups list on left, details on right
        split_layout = QHBoxLayout()
        
        # Left panel: Backup history
        left_panel = self._create_backup_list_panel()
        split_layout.addWidget(left_panel, 1)
        
        # Right panel: Backup details
        right_panel = self._create_details_panel()
        split_layout.addWidget(right_panel, 2)
        
        main_layout.addLayout(split_layout)
        
        # Load backups
        self._refresh_backup_list()
        
        return main_widget
    
    def _create_backup_list_panel(self) -> QWidget:
        """Create left panel with backup history list."""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(SubtitleLabel("Backup History"))
        header_layout.addStretch()
        
        from qfluentwidgets import TransparentToolButton
        refresh_btn = TransparentToolButton(FIF.SYNC, self._parent)
        refresh_btn.setFixedSize(32, 32)
        refresh_btn.setToolTip("Refresh List")
        refresh_btn.installEventFilter(ToolTipFilter(refresh_btn, showDelay=300))
        refresh_btn.clicked.connect(self._refresh_backup_list)
        header_layout.addWidget(refresh_btn)
        layout.addLayout(header_layout)
        
        # Backup list
        self.backup_list = ListWidget()
        self.backup_list.setAlternatingRowColors(True)
        self.backup_list.currentRowChanged.connect(self._on_backup_selected)
        layout.addWidget(self.backup_list)
        
        # Actions
        btn_layout = QHBoxLayout()
        
        delete_old_btn = PushButton(FIF.DELETE, "Delete Old")
        delete_old_btn.setFixedHeight(32)
        delete_old_btn.clicked.connect(self._delete_old_backups)
        btn_layout.addWidget(delete_old_btn)
        
        layout.addLayout(btn_layout)
        
        return card
    
    def _create_details_panel(self) -> QWidget:
        """Create right panel with backup details and restore options."""
        card = CardWidget()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        layout.addWidget(SubtitleLabel("Backup Details"))
        
        # Info section (will be populated when backup is selected)
        self.info_widget = QWidget()
        info_layout = QVBoxLayout(self.info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)
        
        self.info_label = BodyLabel("Select a backup from the list to view details")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label)
        
        layout.addWidget(self.info_widget)
        
        # Files list with checkboxes
        files_header_layout = QHBoxLayout()
        files_header_layout.addWidget(StrongBodyLabel("Files to Restore"))
        files_header_layout.addStretch()
        
        self.select_all_btn = PushButton("Select All")
        self.select_all_btn.setFixedSize(100, 28)
        self.select_all_btn.clicked.connect(self._select_all_files)
        self.select_all_btn.setEnabled(False)
        files_header_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = PushButton("Deselect All")
        self.deselect_all_btn.setFixedSize(100, 28)
        self.deselect_all_btn.clicked.connect(self._deselect_all_files)
        self.deselect_all_btn.setEnabled(False)
        files_header_layout.addWidget(self.deselect_all_btn)
        
        layout.addLayout(files_header_layout)
        
        # Scrollable file list - styled with theme awareness
        from PyQt6.QtWidgets import QScrollArea
        from qfluentwidgets import isDarkTheme, qconfig, Theme
        
        self.files_scroll = QScrollArea()
        self.files_scroll.setWidgetResizable(True)
        self.files_scroll.setMinimumHeight(200)
        self.files_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.files_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.files_widget = QWidget()
        self.files_layout = QVBoxLayout(self.files_widget)
        self.files_layout.setContentsMargins(8, 8, 8, 8)
        self.files_layout.setSpacing(4)
        self.files_layout.addStretch()
        
        # Apply initial theme styling
        self._apply_files_scroll_theme()
        
        self.files_scroll.setWidget(self.files_widget)
        layout.addWidget(self.files_scroll)
        
        # Connect to theme changes
        qconfig.themeChangedFinished.connect(self._apply_files_scroll_theme)
        
        # Conflict strategy
        strategy_layout = QHBoxLayout()
        strategy_layout.addWidget(BodyLabel("If file exists at original location"))
        
        self.conflict_combo = ComboBox()
        self.conflict_combo.addItems(["Skip", "Overwrite", "Rename"])
        self.conflict_combo.setCurrentIndex(0)
        self.conflict_combo.setFixedWidth(150)
        self.conflict_combo.setEnabled(False)
        strategy_layout.addWidget(self.conflict_combo)
        strategy_layout.addStretch()
        layout.addLayout(strategy_layout)
        
        # Restore buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.restore_selected_btn = PrimaryPushButton(FIF.SYNC, "Restore Selected")
        self.restore_selected_btn.setFixedSize(160, 36)
        self.restore_selected_btn.clicked.connect(self._restore_selected)
        self.restore_selected_btn.setEnabled(False)
        btn_layout.addWidget(self.restore_selected_btn)
        
        self.restore_all_btn = PushButton(FIF.SYNC, "Restore All")
        self.restore_all_btn.setFixedSize(140, 36)
        self.restore_all_btn.clicked.connect(self._restore_all)
        self.restore_all_btn.setEnabled(False)
        btn_layout.addWidget(self.restore_all_btn)
        
        layout.addLayout(btn_layout)
        
        return card
    
    def _refresh_backup_list(self) -> None:
        """Refresh the backup list from disk."""
        self.backup_list.clear()
        backups = self.recovery_manager.get_all_backups()
        
        if not backups:
            self.info_label.setText("No backups found. Backups are created automatically when you organize files.")
            return
        
        for backup in backups:
            # Format: "Nov 13, 2025 2:23 PM - 128 files"
            item_text = f"{backup.display_time} - {backup.total_files} files"
            self.backup_list.addItem(item_text)
        
        self.logger.info(f"Loaded {len(backups)} backup(s)")
    
    def _on_backup_selected(self, index: int) -> None:
        """Handle backup selection from list."""
        if index < 0:
            return
        
        backups = self.recovery_manager.get_all_backups()
        if index >= len(backups):
            return
        
        self.current_backup = backups[index]
        self._display_backup_details(self.current_backup)
    
    def _display_backup_details(self, backup) -> None:
        """Display details of selected backup."""
        from app.core.recovery_manager import BackupInfo
        
        # Update info label
        stats = self.recovery_manager.get_backup_stats(backup)
        info_text = (
            f"Timestamp: {backup.display_time}\n"
            f"Source: {backup.source}\n"
            f"Destination: {backup.destination}\n"
            f"Total Files: {backup.total_files}\n"
            f"At Destination: {stats['at_destination']}\n"
            f"Missing: {stats['missing']}\n"
            f"Backup Size: {backup.file_size_kb:.2f} KB"
        )
        self.info_label.setText(info_text)
        
        self.logger.info(f"Loading backup with {len(backup.file_movements)} file movements")
        
        # Clear previous file checkboxes
        for checkbox in self.file_checkboxes:
            checkbox.deleteLater()
        self.file_checkboxes.clear()
        
        # Remove stretch temporarily
        stretch_item = self.files_layout.takeAt(self.files_layout.count() - 1)
        
        # Add file checkboxes
        if not backup.file_movements:
            no_files_label = BodyLabel("No file movements recorded in this backup")
            self.files_layout.addWidget(no_files_label)
            self.file_checkboxes.append(no_files_label)  # Store for cleanup
        else:
            for movement in backup.file_movements:
                original_path = Path(movement.original)
                dest_path = Path(movement.destination)
                
                # Status: Prioritize backup copy, then check destination
                if movement.has_backup_copy:
                    status = "[Backed Up]"
                    can_restore = True
                    status_msg = f"✓ File backup exists - can be fully restored\nBackup: {movement.backup_filename}\nOriginal location: {movement.original}"
                elif movement.exists_at_destination:
                    status = "[Available]"
                    can_restore = True
                    status_msg = f"File is at organized location: {movement.destination}\nCan be restored back to: {movement.original}"
                else:
                    status = "[Missing]"
                    can_restore = False
                    status_msg = f"File not found and no backup exists\nOriginal: {movement.original}\nLast known location: {movement.destination}"
                
                checkbox = CheckBox(f"{status} {original_path.name} -> {movement.category}")
                checkbox.setEnabled(can_restore)
                checkbox.setChecked(can_restore)
                checkbox.setToolTip(status_msg)
                checkbox.installEventFilter(ToolTipFilter(checkbox))
                
                self.files_layout.addWidget(checkbox)
                self.file_checkboxes.append(checkbox)
        
        # Add stretch back
        if stretch_item:
            self.files_layout.addItem(stretch_item)
        else:
            self.files_layout.addStretch()
        
        # Enable controls
        self.select_all_btn.setEnabled(True)
        self.deselect_all_btn.setEnabled(True)
        self.conflict_combo.setEnabled(True)
        self.restore_selected_btn.setEnabled(True)
        self.restore_all_btn.setEnabled(True)
    
    def _apply_files_scroll_theme(self) -> None:
        """Apply theme-aware styling to files scroll area - matching activity log."""
        from qfluentwidgets import isDarkTheme
        from PyQt6.QtGui import QPalette, QColor
        
        # Use exact same colors as ColoredPlainTextEdit (activity log)
        if isDarkTheme():
            border_color = "rgb(60, 63, 68)"
            bg_color = "rgb(38, 39, 43)"
        else:
            border_color = "rgb(229, 231, 235)"
            bg_color = "rgb(248, 249, 250)"
        
        # Use QPalette for background like ColoredPlainTextEdit
        palette = self.files_widget.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(bg_color.replace("rgb(", "").replace(")", "")))
        self.files_widget.setPalette(palette)
        self.files_widget.setAutoFillBackground(True)
        
        # Apply border and styling - matching activity log exactly
        self.files_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
            }}
        """)
        self.files_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_color};
                border-radius: 6px;
            }}
        """)
    
    def _select_all_files(self) -> None:
        """Select all available files for restoration."""
        for checkbox in self.file_checkboxes:
            if hasattr(checkbox, 'isEnabled') and hasattr(checkbox, 'setChecked'):
                if checkbox.isEnabled():
                    checkbox.setChecked(True)
    
    def _deselect_all_files(self) -> None:
        """Deselect all files."""
        for checkbox in self.file_checkboxes:
            if hasattr(checkbox, 'setChecked'):
                checkbox.setChecked(False)
    
    def _restore_selected(self) -> None:
        """Restore selected files from backup."""
        if not self.current_backup:
            return
        
        # Get selected file indices - only count actual checkboxes
        selected_indices = [
            i for i, cb in enumerate(self.file_checkboxes) 
            if hasattr(cb, 'isChecked') and cb.isChecked()
        ]
        
        if not selected_indices:
            InfoBar.warning(
                title="No Files Selected",
                content="Please select at least one file to restore.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
            return
        
        # Confirm restoration
        w = MessageBox(
            "Confirm Restoration",
            f"Restore {len(selected_indices)} file(s) from backup?\n\n"
            f"Files will be moved from destination back to their original locations.",
            self._parent
        )
        if w.exec():
            self._perform_restore(selected_indices)
    
    def _restore_all(self) -> None:
        """Restore all available files from backup."""
        if not self.current_backup:
            return
        
        # Get all available file indices
        available_indices = [
            i for i, movement in enumerate(self.current_backup.file_movements)
            if movement.exists_at_destination
        ]
        
        if not available_indices:
            InfoBar.warning(
                title="No Files Available",
                content="No files are available to restore from this backup.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
            return
        
        # Confirm restoration
        w = MessageBox(
            "Confirm Restoration",
            f"Restore all {len(available_indices)} available file(s) from backup?\n\n"
            f"Files will be moved from destination back to their original locations.",
            self._parent
        )
        if w.exec():
            self._perform_restore(available_indices)
    
    def _perform_restore(self, indices: List[int]) -> None:
        """Perform the actual file restoration.
        
        Args:
            indices: List of file indices to restore
        """
        conflict_strategy = self.conflict_combo.currentText().lower()
        
        try:
            stats = self.recovery_manager.restore_files(
                self.current_backup,
                indices,
                conflict_strategy
            )
            
            # Show results
            w = MessageBox(
                "Restoration Complete",
                f"Restoration finished!\n\n"
                f"Restored: {stats['restored']}\n"
                f"Skipped: {stats['skipped']}\n"
                f"Errors: {stats['errors']}",
                self._parent
            )
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
            
            # Refresh the display
            self._on_backup_selected(self.backup_list.currentRow())
            
        except Exception as e:
            w = MessageBox("Restoration Failed", f"An error occurred:\n{str(e)}", self._parent)
            w.cancelButton.hide()
            w.yesButton.setText("OK")
            w.exec()
    
    def _delete_old_backups(self) -> None:
        """Delete old backup files, keeping the 10 most recent."""
        # Get current backup count
        current_count = len(self.recovery_manager.get_all_backups())
        
        if current_count <= 10:
            InfoBar.warning(
                title="No Old Backups",
                content=f"You have {current_count} backup(s). Only backups beyond 10 will be deleted.",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
            return
        
        w = MessageBox(
            "Delete Old Backups",
            f"You have {current_count} backups. Delete old backup files, keeping only the 10 most recent?\n\n"
            "This action cannot be undone.",
            self._parent
        )
        
        # exec() returns True if Yes button clicked, False if No/Cancel
        if w.exec():
            deleted = self.recovery_manager.delete_old_backups(keep_count=10)
            
            InfoBar.success(
                title="Cleanup Complete",
                content=f"Deleted {deleted} old backup file(s).",
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self._parent
            )
            
            self._refresh_backup_list()
            self.logger.info(f"Deleted {deleted} old backup(s), kept 10 most recent")


