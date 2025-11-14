"""About page with application information and credits."""
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QCursor

from qfluentwidgets import (
    BodyLabel, TitleLabel, SubtitleLabel, StrongBodyLabel,
    SmoothScrollArea, HyperlinkLabel, isDarkTheme, MessageBox
)
from qfluentwidgets import FluentIcon as FIF

from app.ui.theme_utils import apply_page_theme, apply_message_box_theme
from app.ui.widgets import ThemedCardWidget

class AboutPage:
    """About page with project information and credits"""
    
    def __init__(self, parent=None) -> None:
        """Initialize about page
        
        Args:
            parent: Parent widget for dialogs
        """
        self.parent = parent
        self.scroll_area = None
        self.content_widget = None
    
    def _get_text_color(self) -> str:
        """Get appropriate text color based on current theme
        
        Returns:
            Color string for text
        """
        from qfluentwidgets import isDarkTheme
        return "rgb(230, 230, 230)" if isDarkTheme() else "rgb(30, 30, 30)"
    
    def create(self) -> QWidget:
        """Create about page widget
        
        Returns:
            About page widget
        """
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("pageScrollArea")
        
        widget = QWidget()
        widget.setObjectName("pageContentWidget")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 24, 32, 24)
        layout.setSpacing(20)

        layout.addWidget(TitleLabel("About"))
        
        # App Info Card
        layout.addWidget(self._create_app_info_card())
        
        # Credits Card
        layout.addWidget(self._create_credits_card())
        
        layout.addStretch()
        
        scroll.setWidget(widget)
        self.scroll_area = scroll
        self.content_widget = widget
        apply_page_theme(widget, scroll)
        return scroll
    
    def _create_app_info_card(self) -> ThemedCardWidget:
        """Create app information card
        
        Returns:
            App info card widget
        """
        card = ThemedCardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        
        # Title
        card_layout.addWidget(SubtitleLabel("File Organizer"))
        
        # Get text color for theme
        text_color = self._get_text_color()
        
        # Version
        version_layout = QHBoxLayout()
        version_label = StrongBodyLabel("Version")
        version_value = BodyLabel("2.7.1")
        version_layout.addWidget(version_label)
        version_layout.addWidget(version_value)
        version_layout.addStretch()
        card_layout.addLayout(version_layout)
        
        # Release Date
        date_layout = QHBoxLayout()
        date_label = StrongBodyLabel("Release Date")
        date_value = BodyLabel("November 2025")
        date_layout.addWidget(date_label)
        date_layout.addWidget(date_value)
        date_layout.addStretch()
        card_layout.addLayout(date_layout)
        
        # Description
        description = BodyLabel("An open source project for organizing files by category. Helps you keep your files organized and easy to find.")
        description.setWordWrap(True)
        card_layout.addWidget(description)
        
        # GitHub Link - Clickable hyperlink with safety confirmation
        github_layout = QHBoxLayout()
        github_label = StrongBodyLabel("Repository")
        
        # Create clickable link using BodyLabel with custom click handler
        from PyQt6.QtWidgets import QLabel
        from PyQt6.QtCore import Qt
        
        class ClickableLabel(QLabel):
            def __init__(self, text, callback):
                super().__init__(text)
                self.callback = callback
                self.setCursor(Qt.CursorShape.PointingHandCursor)
                
            def mousePressEvent(self, event):
                if event.button() == Qt.MouseButton.LeftButton:
                    self.callback()
        
        github_link = ClickableLabel(
            '<a href="#" style="color: #009faa; text-decoration: none;">https://github.com/franklinnolasco7/FileOrganizer</a>',
            lambda: self._open_external_link("https://github.com/franklinnolasco7/FileOrganizer")
        )
        github_link.setTextFormat(Qt.TextFormat.RichText)
        
        github_layout.addWidget(github_label)
        github_layout.addWidget(github_link)
        github_layout.addStretch()
        card_layout.addLayout(github_layout)
        
        return card
    
    def _create_credits_card(self) -> ThemedCardWidget:
        """Create credits card
        
        Returns:
            Credits card widget
        """
        card = ThemedCardWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)
        
        card_layout.addWidget(SubtitleLabel("Credits"))
        
        # Get text color for theme
        text_color = self._get_text_color()
        
        # Developer
        dev_layout = QHBoxLayout()
        dev_label = StrongBodyLabel("Developer")
        dev_name = BodyLabel("Franklin Nolasco")
        dev_layout.addWidget(dev_label)
        dev_layout.addWidget(dev_name)
        dev_layout.addStretch()
        card_layout.addLayout(dev_layout)
        
        # Framework
        framework_layout = QHBoxLayout()
        framework_label = StrongBodyLabel("Framework")
        framework_value = BodyLabel("PyQt6")
        framework_layout.addWidget(framework_label)
        framework_layout.addWidget(framework_value)
        framework_layout.addStretch()
        card_layout.addLayout(framework_layout)
        
        # UI Theme
        theme_layout = QHBoxLayout()
        theme_label = StrongBodyLabel("UI Theme")
        theme_value = BodyLabel("qfluentwidgets")
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(theme_value)
        theme_layout.addStretch()
        card_layout.addLayout(theme_layout)
        
        # Type
        type_layout = QHBoxLayout()
        type_label = StrongBodyLabel("Type")
        type_value = BodyLabel("Open Source")
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_value)
        type_layout.addStretch()
        card_layout.addLayout(type_layout)
        
        return card
    
    def _open_external_link(self, url: str) -> None:
        """Open external URL with safety confirmation dialog
        
        Args:
            url: URL to open
        """
        # Use qfluentwidgets MessageBox for proper theming
        w = MessageBox(
            "Open External Link",
            f"You are about to open an external link:\n\n{url}\n\nDo you want to continue?",
            self.parent
        )
        apply_message_box_theme(w)
        w.yesButton.setText("Yes")
        w.cancelButton.setText("No")
        
        if w.exec():
            QDesktopServices.openUrl(QUrl(url))


# Import FluentWindow here to avoid creating widgets before QApplication
# from qfluentwidgets import FluentWindow


