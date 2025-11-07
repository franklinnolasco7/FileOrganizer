"""
Operation History - Memento pattern for undo/redo
Tracks file operations for rollback functionality
"""
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class FileOperation:
    """Single file operation record"""
    source: Path
    destination: Path
    timestamp: datetime
    category: str
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "source": str(self.source),
            "destination": str(self.destination),
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
        }


class OperationHistory:
    """
    Manage operation history for undo/redo.
    Memento pattern implementation.
    """
    
    def __init__(self, max_operations: int = 1000) -> None:
        """
        Initialize operation history.
        
        Args:
            max_operations: Maximum operations to keep in history
        """
        self.max_operations = max_operations
        self._history: List[List[FileOperation]] = []
        self._current_index = -1
    
    def start_batch(self) -> None:
        """Start a new batch of operations (one organize action)"""
        # Remove any "future" history if we're not at the end
        if self._current_index < len(self._history) - 1:
            self._history = self._history[:self._current_index + 1]
        
        # Start new batch
        self._history.append([])
        self._current_index = len(self._history) - 1
        
        # Trim if exceeding max
        if len(self._history) > self.max_operations:
            self._history.pop(0)
            self._current_index -= 1
    
    def record_operation(
        self,
        source: Path,
        destination: Path,
        category: str,
    ) -> None:
        """
        Record a single file operation.
        
        Args:
            source: Original file location
            destination: New file location
            category: File category
        """
        if self._current_index < 0 or not self._history:
            self.start_batch()
        
        operation = FileOperation(
            source=source,
            destination=destination,
            timestamp=datetime.now(),
            category=category,
        )
        
        self._history[self._current_index].append(operation)
    
    def can_undo(self) -> bool:
        """Check if undo is available"""
        return self._current_index >= 0 and bool(self._history)
    
    def can_redo(self) -> bool:
        """Check if redo is available"""
        return self._current_index < len(self._history) - 1
    
    def get_undo_batch(self) -> Optional[List[FileOperation]]:
        """
        Get current batch for undo.
        
        Returns:
            List of operations to undo, or None if no undo available
        """
        if not self.can_undo():
            return None
        
        return self._history[self._current_index]
    
    def get_redo_batch(self) -> Optional[List[FileOperation]]:
        """
        Get next batch for redo.
        
        Returns:
            List of operations to redo, or None if no redo available
        """
        if not self.can_redo():
            return None
        
        return self._history[self._current_index + 1]
    
    def mark_undo_complete(self) -> None:
        """Mark current batch as undone"""
        if self.can_undo():
            self._current_index -= 1
    
    def mark_redo_complete(self) -> None:
        """Mark next batch as redone"""
        if self.can_redo():
            self._current_index += 1
    
    def clear(self) -> None:
        """Clear all history"""
        self._history.clear()
        self._current_index = -1
    
    def get_operation_count(self) -> int:
        """Get total number of operations in current batch"""
        if self._current_index >= 0 and self._current_index < len(self._history):
            return len(self._history[self._current_index])
        return 0
    
    def get_last_operation_summary(self) -> str:
        """
        Get summary of last operation batch.
        
        Returns:
            Human-readable summary
        """
        if not self.can_undo():
            return "No operations"
        
        batch = self._history[self._current_index]
        count = len(batch)
        
        if count == 0:
            return "No files"
        
        return f"{count} file{'s' if count != 1 else ''}"
