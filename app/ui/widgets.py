"""Custom widgets for File Organizer UI"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QPlainTextEdit, QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QTextCursor, QColor, QTextCharFormat, QDragEnterEvent, 
    QDropEvent, QPainter, QPen, QPalette
)
from qfluentwidgets import LineEdit, PlainTextEdit, CardWidget, TitleLabel, BodyLabel, IconWidget
from qfluentwidgets import FluentIcon as FIF


class DragDropLineEdit(LineEdit):
    """LineEdit with enhanced drag and drop support for folders."""
    
    def __init__(self, *args, **kwargs):
        """Initialize drag-drop enabled line edit."""
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self._is_dragging = False
        self.setFixedHeight(38)
        self._drag_state = None  # 'valid', 'invalid', or None
        self._dash_offset = 0
        
        # Animation timer for marching ants effect
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(50)  # Update every 50ms for smooth animation
        self._animation_timer.timeout.connect(self._animate_border)
    
    def _animate_border(self):
        """Animate the border with marching ants effect."""
        self._dash_offset += 1
        if self._dash_offset >= 12:  # Reset after full dash cycle
            self._dash_offset = 0
        self.update()
    
    def paintEvent(self, event):
        """Custom paint to add animated overlay border."""
        super().paintEvent(event)
        
        if self._drag_state:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Choose color based on state
            if self._drag_state == 'valid':
                color = QColor(46, 160, 67)
            elif self._drag_state == 'invalid':
                color = QColor(208, 68, 55)
            else:  # success
                color = QColor(46, 160, 67)
            
            # Create animated dash pattern
            pen = QPen(color)
            pen.setWidth(3)
            
            if self._drag_state != 'success':
                # Marching ants: dash pattern with offset
                pen.setStyle(Qt.PenStyle.CustomDashLine)
                pen.setDashPattern([6, 6])  # 6px dash, 6px gap
                pen.setDashOffset(self._dash_offset)
            else:
                pen.setStyle(Qt.PenStyle.SolidLine)
            
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Draw rectangle with slight inset for border
            rect = QRectF(1.5, 1.5, self.width() - 3, self.height() - 3)
            painter.drawRoundedRect(rect, 5, 5)
    
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Handle drag enter with visual feedback."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                path = Path(urls[0].toLocalFile())
                if path.is_dir():
                    event.acceptProposedAction()
                    self._is_dragging = True
                    self._drag_state = 'valid'
                    self._dash_offset = 0
                    self._animation_timer.start()
                    self.setPlaceholderText("✓ Drop folder here...")
                else:
                    event.ignore()
                    self._is_dragging = True
                    self._drag_state = 'invalid'
                    self._dash_offset = 0
                    self._animation_timer.start()
                    self.setPlaceholderText("✗ Folders only")
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
        self._drag_state = None
        self._animation_timer.stop()
        self.update()
        self._reset_placeholder()
    
    def dropEvent(self, event) -> None:
        """Handle drop with validation and feedback."""
        self._is_dragging = False
        self._animation_timer.stop()
        
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                folder_path = Path(urls[0].toLocalFile())
                if folder_path.is_dir():
                    self.setText(str(folder_path))
                    event.acceptProposedAction()
                    
                    # Brief success feedback
                    self._drag_state = 'success'
                    self.update()
                    self._reset_placeholder()
                    
                    QTimer.singleShot(500, lambda: (
                        setattr(self, '_drag_state', None),
                        self.update()
                    ))
                else:
                    event.ignore()
                    self._drag_state = None
                    self.update()
                    self._reset_placeholder()
        else:
            event.ignore()
            self._drag_state = None
            self.update()
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
    
    def __init__(self) -> None:
        """Initialize colored text edit"""
        super().__init__()
        self.setReadOnly(True)
        self.setMinimumHeight(150)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setMaximumBlockCount(500)
        
        # Remove default document margins to eliminate unnecessary spacing
        self.document().setDocumentMargin(0)
        
        # Theme-aware colors for better readability
        # These colors work well in both light and dark themes
        self.COLORS_LIGHT = {
            "INFO": QColor("#5B6C7D"),      # Muted blue-gray for info
            "SUCCESS": QColor("#2D7A3E"),   # Darker green for success
            "WARNING": QColor("#C87700"),   # Darker orange for warning
            "ERROR": QColor("#D32F2F"),     # Strong red for errors
            "DEBUG": QColor("#757575"),     # Medium gray for debug
        }
        
        self.COLORS_DARK = {
            "INFO": QColor("#B0B0B0"),      # Light gray for info
            "SUCCESS": QColor("#4CAF50"),   # Bright green for success
            "WARNING": QColor("#FF9800"),   # Bright orange for warning
            "ERROR": QColor("#F44336"),     # Bright red for errors
            "DEBUG": QColor("#888888"),     # Light gray for debug
        }
        
        # Set initial colors and border based on theme
        self._update_colors()
        self._apply_border_style()
    
    def _apply_border_style(self) -> None:
        """Apply visible border styling based on current theme"""
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            border_color = "rgb(60, 63, 68)"
            bg_color = "rgb(38, 39, 43)"
        else:
            border_color = "rgb(229, 231, 235)"
            bg_color = "rgb(248, 249, 250)"  # Slightly gray background for contrast
        
        # Use QPalette for background
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(bg_color.replace("rgb(", "").replace(")", "")))
        self.setPalette(palette)
        
        # Apply rounded corners - 6px for nested input elements (cards use 8px)
        self.setStyleSheet(f"""
            ColoredPlainTextEdit, PlainTextEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 8px;
            }}
        """)
    
    def _update_colors(self) -> None:
        """Update colors based on current theme"""
        from qfluentwidgets import isDarkTheme
        self.COLORS = self.COLORS_DARK if isDarkTheme() else self.COLORS_LIGHT
        # Also update border when colors update
        self._apply_border_style()
    
    def append_colored(self, message: str) -> None:
        """Append message with color based on log level."""
        # Update colors in case theme changed
        self._update_colors()
        
        level = self._extract_level(message)
        formatted_msg = self._strip_timestamp(message)
        
        self.blockSignals(True)
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        fmt = QTextCharFormat()
        fmt.setForeground(self.COLORS.get(level, self.COLORS["INFO"]))
        
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
    """Dialog showing file organization preview with modern fluent design."""
    
    def __init__(self, preview_data: dict, parent=None):
        """Initialize preview dialog with file data."""
        super().__init__(parent)
        self.setWindowTitle("File Organization Preview")
        self.resize(950, 650)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # Header with title
        title_text = f"Found {preview_data['total']} files to organize"
        if preview_data.get('skipped_by_size', 0) > 0:
            title_text += f" ({preview_data['skipped_by_size']} skipped by size filter)"
        title = TitleLabel(title_text)
        layout.addWidget(title)
        
        # Category summary in a modern card
        if preview_data['summary']:
            summary_card = self._create_summary_card(preview_data['summary'])
            layout.addWidget(summary_card)
        
        # File list section with header
        if preview_data['files']:
            file_header = BodyLabel("File Details")
            file_header.setStyleSheet("font-size: 14px; font-weight: 600; margin-top: 8px;")
            layout.addWidget(file_header)
            
            table = self._create_file_table(preview_data['files'])
            layout.addWidget(table, 1)
    
    def _create_summary_card(self, summary: dict) -> CardWidget:
        """Create modern summary card with category counts."""
        from qfluentwidgets import isDarkTheme
        
        card = CardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)
        
        # Text color based on theme
        text_color = "rgb(230, 230, 230)" if isDarkTheme() else "rgb(30, 30, 30)"
        
        # Header
        header = BodyLabel("Files per Category")
        header.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {text_color};")
        card_layout.addWidget(header)
        
        # Category chips in a flow layout
        chips_layout = QHBoxLayout()
        chips_layout.setSpacing(12)
        
        # Icon and color mapping for categories
        category_styles = {
            'Archives': (FIF.ZIP_FOLDER, 'rgb(255, 159, 64)'),
            'Code': (FIF.CODE, 'rgb(75, 192, 192)'),
            'Documents': (FIF.DOCUMENT, 'rgb(54, 162, 235)'),
            'Images': (FIF.PHOTO, 'rgb(255, 99, 132)'),
            'Music': (FIF.MUSIC, 'rgb(153, 102, 255)'),
            'Videos': (FIF.VIDEO, 'rgb(255, 205, 86)'),
            'Others': (FIF.FOLDER, 'rgb(201, 203, 207)'),
        }
        
        # Text color based on theme
        text_color = "rgb(230, 230, 230)" if isDarkTheme() else "rgb(30, 30, 30)"
        
        for category, count in summary.items():
            icon, color = category_styles.get(category, (FIF.FOLDER, 'rgb(150, 150, 150)'))
            
            # Create chip container
            chip = QWidget()
            chip_layout = QHBoxLayout(chip)
            chip_layout.setContentsMargins(12, 6, 12, 6)
            chip_layout.setSpacing(8)
            
            # Icon
            icon_widget = IconWidget(icon)
            icon_widget.setFixedSize(16, 16)
            chip_layout.addWidget(icon_widget)
            
            # Category text
            label = BodyLabel(category)
            label.setStyleSheet(f"font-weight: 500; color: {text_color};")
            chip_layout.addWidget(label)
            
            # Count badge
            count_label = BodyLabel(str(count))
            count_label.setStyleSheet(f"""
                background-color: {color};
                color: white;
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: 600;
                font-size: 12px;
            """)
            chip_layout.addWidget(count_label)
            
            chips_layout.addWidget(chip)
        
        chips_layout.addStretch()
        card_layout.addLayout(chips_layout)
        
        return card
    
    def _create_file_table(self, files: list) -> QTableWidget:
        """Create modern table showing files and their destinations."""
        from qfluentwidgets import isDarkTheme
        
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["File Name", "Size (KB)", "Current Location", "Destination Category"])
        table.setRowCount(len(files))
        
        # Style the table for better appearance
        bg_color = "rgb(38, 39, 43)" if isDarkTheme() else "rgb(255, 255, 255)"
        alt_color = "rgb(45, 46, 50)" if isDarkTheme() else "rgb(248, 249, 250)"
        border_color = "rgb(60, 63, 68)" if isDarkTheme() else "rgb(229, 231, 235)"
        text_color = "rgb(230, 230, 230)" if isDarkTheme() else "rgb(30, 30, 30)"
        header_bg = "rgb(48, 49, 53)" if isDarkTheme() else "rgb(243, 244, 246)"
        
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                gridline-color: {border_color};
                color: {text_color};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 8px;
                border: none;
                outline: none;
            }}
            QTableWidget::item:selected {{
                background-color: rgba(0, 159, 170, 0.2);
                outline: none;
            }}
            QTableWidget::item:focus {{
                outline: none;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {text_color};
                padding: 10px;
                border: none;
                border-bottom: 2px solid {border_color};
                font-weight: 600;
                font-size: 12px;
            }}
        """)
        
        table.setAlternatingRowColors(True)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(True)
        
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
            
            # Category with color badge
            cat_item = QTableWidgetItem(f"  {file_info['category']}")
            table.setItem(row, 3, cat_item)
        
        # Resize columns
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        return table
