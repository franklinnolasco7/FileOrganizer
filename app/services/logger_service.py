"""Logging service with observer pattern and bounded history."""
from typing import Callable, List
from datetime import datetime
from collections import deque
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class LoggerService:
    """Centralized logging with observer pattern.
    
    Multiple subscribers notified on each log. Circular buffer prevents
    memory leaks by keeping only recent entries.
    """
    
    def __init__(self, max_history: int = 1000) -> None:
        """Initialize logger service.
        
        Args:
            max_history: Maximum log entries to keep (circular buffer)
        """
        if max_history < 10:
            raise ValueError("max_history must be at least 10")

        self._subscribers: List[Callable[[str], None]] = []
        self._log_history: deque = deque(maxlen=max_history)
        self.max_history = max_history

    def subscribe(self, callback: Callable[[str], None]) -> None:
        """Subscribe to log events (idempotent - no duplicates).
        
        Args:
            callback: Function called on every log event
        """
        if callback not in self._subscribers:
            self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[str], None]) -> None:
        """Unsubscribe from log events (safe - no error if not found).
        
        Args:
            callback: Callback to remove
        """
        try:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        except (ValueError, AttributeError):
            pass

    def _notify_subscribers(self, message: str, level: LogLevel) -> None:
        """Notify all subscribers; trap exceptions so one failure doesn't break others.
        
        Args:
            message: Formatted log message
            level: Log level for filtering (optional for future use)
        """
        for subscriber in self._subscribers[:]:  # Iterate over copy to allow unsubscribe during callback
            try:
                subscriber(message)
            except Exception as e:
                print(f"[LoggerService] Subscriber error: {str(e)}")

    def _log(self, level: LogLevel, message: str) -> None:
        """Format message and distribute to subscribers and history.
        
        Args:
            level: Log level
            message: Log message
        """
        formatted = self._format_message(level, message)
        self._log_history.append(formatted)
        self._notify_subscribers(formatted, level)

    def debug(self, message: str) -> None:
        """Log debug message"""
        self._log(LogLevel.DEBUG, message)

    def info(self, message: str) -> None:
        """Log info message"""
        self._log(LogLevel.INFO, message)

    def warning(self, message: str) -> None:
        """Log warning message"""
        self._log(LogLevel.WARNING, message)

    def error(self, message: str) -> None:
        """Log error message"""
        self._log(LogLevel.ERROR, message)

    def success(self, message: str) -> None:
        """Log success message"""
        self._log(LogLevel.SUCCESS, message)

    def separator(self) -> None:
        """Log visual separator"""
        separator = "═" * 100
        self._log_history.append(separator)
        for subscriber in self._subscribers[:]:  # Iterate over copy
            try:
                subscriber(separator)
            except Exception as e:
                print(f"[LoggerService] Subscriber error: {str(e)}")

    @staticmethod
    def _format_message(level: LogLevel, message: str) -> str:
        """Format log message with timestamp and level.
        
        Args:
            level: Log level
            message: Log message
            
        Returns:
            Formatted string
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        return f"[{timestamp}] [{level.value}] {message}"

    def get_history(self, last_n: int | None = None) -> List[str]:
        """Get log history from circular buffer.
        
        Args:
            last_n: Return only last N entries (None = all)
            
        Returns:
            List of log entries
        """
        history = list(self._log_history)
        if last_n is not None:
            history = history[-last_n:]
        return history

    def clear_history(self) -> None:
        """Clear log history"""
        self._log_history.clear()
