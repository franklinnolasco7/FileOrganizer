"""Recovery manager for backup and restore functionality"""
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime


@dataclass
class FileMovement:
    """Information about a single file movement"""
    original: str
    destination: str
    category: str
    backup_filename: str
    file_size: int
    
    @property
    def has_backup_copy(self) -> bool:
        """Check if backup copy exists"""
        # This will be checked by RecoveryManager against backup folder
        return bool(self.backup_filename)
    
    @property
    def exists_at_destination(self) -> bool:
        """Check if file exists at destination"""
        return Path(self.destination).exists()


@dataclass
class BackupInfo:
    """Information about a backup"""
    backup_folder: Path
    timestamp: str
    source: str
    destination: str
    total_files: int
    file_movements: List[FileMovement]
    backup_size_bytes: int
    
    @property
    def display_time(self) -> str:
        """Format timestamp for display
        
        Returns:
            Formatted time string like 'Nov 13, 2025 2:23 PM'
        """
        try:
            dt = datetime.strptime(self.timestamp, "%Y%m%d_%H%M%S")
            return dt.strftime("%b %d, %Y %I:%M %p")
        except ValueError:
            return self.timestamp
    
    @property
    def file_size_kb(self) -> float:
        """Get backup size in KB
        
        Returns:
            Size in kilobytes
        """
        return self.backup_size_bytes / 1024


class RecoveryManager:
    """Manages backup and recovery operations"""
    
    def __init__(self, logger, recovery_folder: Path) -> None:
        """Initialize recovery manager
        
        Args:
            logger: Logger service instance
            recovery_folder: Base folder for recovery backups
        """
        self.logger = logger
        self.recovery_folder = Path(recovery_folder)
        self.recovery_folder.mkdir(parents=True, exist_ok=True)
    
    def get_all_backups(self) -> List[BackupInfo]:
        """Get all available backups
        
        Returns:
            List of BackupInfo objects sorted by timestamp (newest first)
        """
        backups = []
        
        if not self.recovery_folder.exists():
            return backups
        
        # Find all backup_* folders
        for backup_dir in self.recovery_folder.glob("backup_*"):
            if not backup_dir.is_dir():
                continue
            
            metadata_file = backup_dir / "metadata.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Build file movements list
                file_movements = []
                files_backup_dir = backup_dir / "files"
                
                for file_data in data.get("files", []):
                    movement = FileMovement(
                        original=file_data["original"],
                        destination=file_data["destination"],
                        category=file_data["category"],
                        backup_filename=file_data.get("backup_filename", ""),
                        file_size=file_data.get("file_size", 0)
                    )
                    file_movements.append(movement)
                
                backup = BackupInfo(
                    backup_folder=backup_dir,
                    timestamp=data["timestamp"],
                    source=data["source"],
                    destination=data["destination"],
                    total_files=data["total_files"],
                    file_movements=file_movements,
                    backup_size_bytes=data.get("backup_size_bytes", 0)
                )
                backups.append(backup)
                
            except Exception as e:
                self.logger.warning(f"Failed to load backup from {backup_dir}: {e}")
                continue
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        
        return backups
    
    def get_backup_stats(self, backup: BackupInfo) -> Dict[str, int]:
        """Get statistics about a backup
        
        Args:
            backup: BackupInfo object
            
        Returns:
            Dictionary with stats (at_destination, missing, etc.)
        """
        stats = {
            "at_destination": 0,
            "missing": 0,
            "has_backup": 0
        }
        
        files_backup_dir = backup.backup_folder / "files"
        
        for movement in backup.file_movements:
            # Check if backup copy exists
            if movement.backup_filename:
                backup_file = files_backup_dir / movement.backup_filename
                if backup_file.exists():
                    stats["has_backup"] += 1
            
            # Check if file exists at destination
            if movement.exists_at_destination:
                stats["at_destination"] += 1
            else:
                stats["missing"] += 1
        
        return stats
    
    def restore_files(
        self,
        backup: BackupInfo,
        indices: List[int],
        conflict_strategy: str = "skip"
    ) -> Dict[str, int]:
        """Restore files from backup
        
        Args:
            backup: BackupInfo object
            indices: List of file indices to restore
            conflict_strategy: How to handle conflicts ("skip", "rename", "replace")
            
        Returns:
            Dictionary with restoration statistics
        """
        stats = {
            "restored": 0,
            "skipped": 0,
            "errors": 0
        }
        
        # Log start of restoration
        self.logger.separator()
        self.logger.info(f"Starting file restoration from backup: {backup.display_time}")
        self.logger.info(f"Files to restore: {len(indices)}")
        self.logger.info(f"Conflict strategy: {conflict_strategy.capitalize()}")
        self.logger.separator()
        
        files_backup_dir = backup.backup_folder / "files"
        
        for idx in indices:
            if idx < 0 or idx >= len(backup.file_movements):
                stats["errors"] += 1
                continue
            
            movement = backup.file_movements[idx]
            original_path = Path(movement.original)
            dest_path = Path(movement.destination)
            
            # Determine source for restoration
            source_for_restore = None
            
            # Priority 1: Use backup copy if available
            if movement.backup_filename:
                backup_file = files_backup_dir / movement.backup_filename
                if backup_file.exists():
                    source_for_restore = backup_file
            
            # Priority 2: Use file at destination if no backup
            if source_for_restore is None and dest_path.exists():
                source_for_restore = dest_path
            
            if source_for_restore is None:
                self.logger.warning(f"Skipped: {original_path.name} - No backup copy or destination file found")
                stats["skipped"] += 1
                continue
            
            # Check if target already exists
            if original_path.exists():
                if conflict_strategy == "skip":
                    self.logger.info(f"Skipped: {original_path.name} - File already exists at original location")
                    stats["skipped"] += 1
                    continue
                elif conflict_strategy == "rename":
                    # Find unique name
                    counter = 1
                    new_path = original_path
                    while new_path.exists():
                        new_path = original_path.parent / f"{original_path.stem}_{counter}{original_path.suffix}"
                        counter += 1
                    self.logger.info(f"Renamed: {original_path.name} → {new_path.name} (conflict avoided)")
                    original_path = new_path
                elif conflict_strategy == "replace":
                    self.logger.info(f"Replacing: {original_path.name} at original location")
            
            try:
                # Ensure parent directory exists
                original_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Copy file back to original location
                shutil.copy2(source_for_restore, original_path)
                
                # Show descriptive restore message
                source_type = "backup" if movement.backup_filename else "destination"
                self.logger.info(f"Restored: {original_path.name} from {source_type} → {original_path.parent}")
                stats["restored"] += 1
                
            except Exception as e:
                self.logger.error(f"Failed to restore {original_path.name}: {e}")
                stats["errors"] += 1
        
        # Log completion summary
        self.logger.separator()
        self.logger.success(f"Restoration Complete!")
        self.logger.info(f"Successfully restored: {stats['restored']} file(s)")
        if stats['skipped'] > 0:
            self.logger.info(f"Skipped: {stats['skipped']} file(s)")
        if stats['errors'] > 0:
            self.logger.error(f"Errors: {stats['errors']} file(s)")
        self.logger.separator()
        
        return stats
    
    def delete_old_backups(self, keep_count: int = 10) -> int:
        """Delete old backups, keeping the most recent ones
        
        Args:
            keep_count: Number of recent backups to keep
            
        Returns:
            Number of backups deleted
        """
        backups = self.get_all_backups()
        
        if len(backups) <= keep_count:
            return 0
        
        # Delete oldest backups
        backups_to_delete = backups[keep_count:]
        deleted_count = 0
        
        for backup in backups_to_delete:
            try:
                shutil.rmtree(backup.backup_folder)
                self.logger.info(f"Deleted old backup: {backup.timestamp}")
                deleted_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to delete backup {backup.timestamp}: {e}")
        
        return deleted_count
