from enum import Enum
from typing import Dict


class ThemeMode(Enum):
    """Theme mode enumeration"""
    LIGHT = "light"
    DARK = "dark"


class ColorScheme:
    """Single color scheme (light or dark)."""
    
    def __init__(
        self,
        bg: str,
        secondary_bg: str,
        text: str,
        text_secondary: str,
        accent: str,
        accent_hover: str,
        success: str,
        warning: str,
        error: str,
        border: str,
        button_fg: str = "white",
    ) -> None:
        """Initialize color scheme.
        
        Args:
            bg: Primary background color
            secondary_bg: Secondary background (cards, panels)
            text: Primary text color
            text_secondary: Secondary text color
            accent: Primary accent color
            accent_hover: Accent color on hover
            success: Success/positive color
            warning: Warning color
            error: Error/negative color
            border: Border color
            button_fg: Button text color
        """
        self.bg = bg
        self.secondary_bg = secondary_bg
        self.text = text
        self.text_secondary = text_secondary
        self.accent = accent
        self.accent_hover = accent_hover
        self.success = success
        self.warning = warning
        self.error = error
        self.border = border
        self.button_fg = button_fg

    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for tkinter/PyQt6 configuration"""
        return {
            "bg": self.bg,
            "secondary_bg": self.secondary_bg,
            "text": self.text,
            "text_secondary": self.text_secondary,
            "accent": self.accent,
            "accent_hover": self.accent_hover,
            "success": self.success,
            "warning": self.warning,
            "error": self.error,
            "border": self.border,
            "fg_text": self.text,
            "button_bg": self.accent,
            "button_fg": self.button_fg,
        }


class ThemeManager:
    """Manage theme modes and notify UI on changes.
    
    Stores both light and dark schemes; observers updated on switch.
    """
    
    def __init__(self) -> None:
        """Initialize theme manager with light and dark schemes"""
        self._current_mode = ThemeMode.DARK
        self._schemes: Dict[ThemeMode, ColorScheme] = {
            ThemeMode.LIGHT: ColorScheme(
                bg="#FFFFFF",
                secondary_bg="#F5F5F5",
                text="#212121",
                text_secondary="#757575",
                accent="#2196F3",
                accent_hover="#1976D2",
                success="#4CAF50",
                warning="#FF9800",
                error="#F44336",
                border="#BDBDBD",
                button_fg="white",
            ),
            ThemeMode.DARK: ColorScheme(
                bg="#1E1E1E",
                secondary_bg="#2D2D2D",
                text="#E0E0E0",
                text_secondary="#B0B0B0",
                accent="#64B5F6",
                accent_hover="#90CAF9",
                success="#81C784",
                warning="#FFB74D",
                error="#EF5350",
                border="#424242",
                button_fg="#1E1E1E",
            ),
        }
        self._observers: list = []

    @property
    def current_theme(self) -> Dict[str, str]:
        """Get current theme colors"""
        return self._schemes[self._current_mode].to_dict()

    @property
    def current_mode(self) -> ThemeMode:
        """Get current theme mode"""
        return self._current_mode

    def set_mode(self, mode: ThemeMode) -> None:
        """Change theme mode and notify observers.
        
        Args:
            mode: New theme mode
        """
        if mode == self._current_mode:
            return

        self._current_mode = mode
        self._notify_observers()

    def get_color(self, key: str) -> str:
        """Get specific color from current theme.
        
        Args:
            key: Color key
            
        Returns:
            Color hex value
            
        Raises:
            KeyError: If color key not found
        """
        color = self.current_theme.get(key)
        if color is None:
            raise KeyError(f"Color '{key}' not found in current theme")
        return color

    def register_observer(self, callback) -> None:
        """Register callback for theme changes.
        
        Args:
            callback: Function to call on theme change
        """
        self._observers.append(callback)

    def _notify_observers(self) -> None:
        """Notify all observers of theme change; trap exceptions."""
        for callback in self._observers:
            try:
                callback(self.current_theme)
            except Exception as e:
                print(f"[ThemeManager] Observer error: {str(e)}")


# Singleton instance for app-wide access
theme_manager = ThemeManager()
