from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
import json
from datetime import datetime
from app.core.constants import FileCategory, JEFF_SU_STRUCTURE
from app.services.logger_service import LoggerService
from app.services.file_service import FileService
from app.core.file_manager import FileManager, FileOperationError
from app.core.operation_history import OperationHistory



class OrganizationError(Exception):
    """Custom exception for organization failures"""
    pass



@dataclass
class OrganizationStats:
    """Statistics container for organization results"""
    moved: int = 0
    skipped: int = 0
    errors: int = 0


    def to_dict(self) -> Dict[str, int]:
        """Convert to dictionary for legacy compatibility"""
        return {"moved": self.moved, "skipped": self.skipped, "errors": self.errors}



class FileOrganizer:
    """Orchestrates file organization by category with undo support"""
    
    def __init__(
        self,
        logger: LoggerService,
        file_service: FileService | None = None,
        file_manager: FileManager | None = None,
        config = None,
    ) -> None:
        """Initialize file organizer with dependencies
        
        Args:
            logger: Service for logging operations
            file_service: Service for file categorization
            file_manager: Service for file operations
            config: Configuration manager for settings
        """
        self.logger = logger
        self.file_service = file_service or FileService()
        self.file_manager = file_manager or FileManager(logger)
        self.history = OperationHistory()
        self._created_folders: Set[Path] = set()
        self.config = config


    def preview_organization(
        self,
        source_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory] | None = None,
        min_size_kb: float = 0,
        max_size_kb: float = 0,
        enable_size_filter: bool = False,
    ) -> Dict:
        """Preview files that will be organized without moving them.
        
        Args:
            source_path: Source folder path
            destination_path: Destination folder path
            active_categories: Categories to organize
            min_size_kb: Minimum file size in KB (0 = no minimum)
            max_size_kb: Maximum file size in KB (0 = no maximum)
            enable_size_filter: Whether to apply size filtering
            
        Returns:
            Dictionary with preview data (total, summary, files)
        """
        validated_source = self._validate_source_path(source_path)
        validated_dest = self._validate_destination_path(destination_path)
        categories = self._validate_categories(active_categories)
        
        files = self.file_manager.get_files_in_folder(validated_source, recursive=True)
        
        preview_data = {
            'total': 0,
            'summary': {},
            'files': [],
            'skipped_by_size': 0
        }
        
        for file_path in files:
            # Check size filter
            if enable_size_filter and not self._passes_size_filter(file_path, min_size_kb, max_size_kb):
                preview_data['skipped_by_size'] += 1
                continue
            
            category = self.file_service.get_file_category(file_path)
            
            # Include file if category is active or OTHERS
            if category in categories or category == FileCategory.OTHERS:
                preview_data['total'] += 1
                
                # Count by category
                cat_name = category.value
                preview_data['summary'][cat_name] = preview_data['summary'].get(cat_name, 0) + 1
                
                # Get file size for display
                file_size_kb = file_path.stat().st_size / 1024
                
                # Add file details
                preview_data['files'].append({
                    'name': file_path.name,
                    'current': str(file_path.parent),
                    'category': cat_name,
                    'size_kb': round(file_size_kb, 2)
                })
        
        return preview_data


    def organize_folder(
        self,
        source_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory] | None = None,
        min_size_kb: float = 0,
        max_size_kb: float = 0,
        enable_size_filter: bool = False,
    ) -> Dict[str, int]:
        """Organize files from source to destination by category
        
        Recursively scans nested folders and cleans up empty directories.
        
        Args:
            source_path: Source folder to organize
            destination_path: Destination folder for organized files
            active_categories: Categories to include (None = all except OTHERS)
            min_size_kb: Minimum file size in KB (0 = no minimum)
            max_size_kb: Maximum file size in KB (0 = no maximum)
            enable_size_filter: Whether to apply size filtering
            
        Returns:
            Dictionary with stats: moved, skipped, errors
            
        Raises:
            OrganizationError: If operation fails
        """
        try:
            self.history.start_batch()
            self._created_folders.clear()
            
            validated_source = self._validate_source_path(source_path)
            validated_dest = self._validate_destination_path(destination_path)
            categories = self._validate_categories(active_categories)


            self.logger.separator()
            self.logger.info("Starting file organization process")
            self.logger.info(f"Source Directory: {validated_source}")
            self.logger.info(f"Destination Directory: {validated_dest}")
            self.logger.info(f"Active Categories: {len(categories)}")
            if enable_size_filter:
                if min_size_kb > 0:
                    self.logger.info(f"Minimum Size Filter: {min_size_kb} KB")
                if max_size_kb > 0:
                    self.logger.info(f"Maximum Size Filter: {max_size_kb} KB")
            self.logger.separator()


            # Now scans nested folders recursively
            files = self.file_manager.get_files_in_folder(validated_source, recursive=True)
            if not files:
                self.logger.warning("No files found in source directory")
                # Remove empty batch since no files were processed
                self.history.remove_empty_current_batch()
                return OrganizationStats().to_dict()


            self.logger.info(f"Scanning Complete: Found {len(files)} file(s) to process")

            # Create recovery backup before processing files
            recovery_file = self._create_recovery_backup(validated_source, validated_dest, files, categories)
            if recovery_file:
                self.logger.info(f"Full backup created: {recovery_file.name}")

            stats = self._process_files(files, validated_dest, categories, min_size_kb, max_size_kb, enable_size_filter)


            # Clean up empty folders after moving all files
            folders_removed = self.file_manager.cleanup_empty_folders(validated_source)
            if folders_removed > 0:
                self.logger.info(f"Cleanup: Removed {folders_removed} empty folder(s)")


            self._log_completion_stats(stats)
            
            # If no files were actually moved, remove the empty batch from history
            # This prevents undo button from being enabled when nothing was done
            if stats.moved == 0:
                self.history.remove_empty_current_batch()
            
            return stats.to_dict()


        except FileOperationError as e:
            self.logger.error(f"File operation failed: {str(e)}")
            raise OrganizationError(f"File operation error: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Organization failed: {str(e)}")
            raise OrganizationError(f"Failed to organize files: {str(e)}") from e


    def _validate_source_path(self, source_path: Path) -> Path:
        """Validate source path exists and is a directory
        
        Args:
            source_path: Path to validate
            
        Returns:
            Resolved absolute path
            
        Raises:
            OrganizationError: If path is invalid
        """
        if not source_path:
            raise OrganizationError("Source path is required")
        if not isinstance(source_path, Path):
            source_path = Path(source_path)


        if not source_path.exists():
            raise OrganizationError(f"Source folder not found: {source_path}")
        if not source_path.is_dir():
            raise OrganizationError(f"Source is not a directory: {source_path}")


        return source_path.resolve()


    def _validate_destination_path(self, dest_path: Path) -> Path:
        """Validate destination path and create if needed
        
        Args:
            dest_path: Destination path to validate
            
        Returns:
            Resolved absolute path
            
        Raises:
            OrganizationError: If path is invalid or cannot be created
        """
        if not dest_path:
            raise OrganizationError("Destination path is required")
        if not isinstance(dest_path, Path):
            dest_path = Path(dest_path)


        if not dest_path.exists():
            try:
                dest_path.mkdir(parents=True, exist_ok=True, mode=0o755)
            except PermissionError:
                raise OrganizationError(f"Permission denied: {dest_path}")
            except OSError as e:
                raise OrganizationError(f"Cannot create destination: {str(e)}")


        if not dest_path.is_dir():
            raise OrganizationError(f"Destination exists but is not a directory: {dest_path}")


        return dest_path.resolve()


    def _validate_categories(
        self,
        categories: List[FileCategory] | None
    ) -> List[FileCategory]:
        """Validate and normalize category list
        
        Args:
            categories: List of categories (None = all except OTHERS)
            
        Returns:
            Validated list of categories
            
        Raises:
            OrganizationError: If categories are invalid
        """
        if categories is None:
            return [cat for cat in FileCategory if cat.name != "OTHERS"]


        if not isinstance(categories, list):
            raise OrganizationError("Categories must be a list")
        if len(categories) == 0:
            raise OrganizationError("At least one category required")


        for cat in categories:
            if not isinstance(cat, FileCategory):
                raise OrganizationError(f"Invalid category: {cat}")


        return categories


    def _process_files(
        self,
        files: List[Path],
        destination_path: Path,
        categories: List[FileCategory],
        min_size_kb: float = 0,
        max_size_kb: float = 0,
        enable_size_filter: bool = False,
    ) -> OrganizationStats:
        """Process and organize each file
        
        Args:
            files: List of file paths to process
            destination_path: Destination folder
            categories: Active categories
            min_size_kb: Minimum file size filter
            max_size_kb: Maximum file size filter
            enable_size_filter: Whether to apply size filters
            
        Returns:
            Organization statistics
        """
        stats = OrganizationStats()


        for file_path in files:
            try:
                # Check size filter
                if enable_size_filter and not self._passes_size_filter(file_path, min_size_kb, max_size_kb):
                    self.logger.debug(f"Skipped: {file_path.name} (size filter)")
                    stats.skipped += 1
                    continue
                
                result = self._organize_file(file_path, destination_path, categories)
                if result == "moved":
                    stats.moved += 1
                elif result == "skipped":
                    stats.skipped += 1


            except Exception as e:
                self.logger.error(f"Failed to organize file '{file_path.name}': {str(e)}")
                stats.errors += 1


        return stats


    def _organize_file(
        self,
        file_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory],
    ) -> str:
        """Move a single file to its category folder
        
        Args:
            file_path: File to organize
            destination_path: Base destination path
            active_categories: Active categories
            
        Returns:
            Status: "moved" or "skipped"
            
        Raises:
            FileOperationError: If file move fails
        """
        category = self.file_service.get_file_category(file_path)


        if category not in active_categories and category != FileCategory.OTHERS:
            self.logger.debug(f"Skipped: {file_path.name} (category inactive)")
            return "skipped"


        category_folder = destination_path / category.value
        
        folder_existed = category_folder.exists()
        category_folder.mkdir(exist_ok=True, parents=True)
        if not folder_existed:
            self._created_folders.add(category_folder)


        destination_file = category_folder / file_path.name
        result = self.file_manager.move_file(source=file_path, destination=destination_file)
        
        if result.success:
            self.history.record_operation(
                source=file_path,
                destination=result.path,
                category=category.value,
            )
            
            self.logger.info(f"Moved: {file_path.name} → {category.value}/")
            return "moved"
        else:
            raise FileOperationError(f"Failed to move {file_path.name}: {result.error}")


    def undo_last_operation(self) -> Dict[str, int]:
        """Undo the last organization operation
        
        Moves files back to original locations and removes empty folders.
        
        Returns:
            Dictionary with stats: restored, errors, folders_removed
            
        Raises:
            OrganizationError: If no operations to undo
        """
        if not self.history.can_undo():
            raise OrganizationError("No operations to undo")
        
        batch = self.history.get_undo_batch()
        if not batch:
            raise OrganizationError("No operations to undo")
        
        self.logger.separator()
        self.logger.info(f"Starting undo operation for {len(batch)} file(s)...")
        
        stats = {"restored": 0, "errors": 0, "folders_removed": 0}
        folders_to_check: Set[Path] = set()
        
        for operation in reversed(batch):
            try:
                folders_to_check.add(operation.destination.parent)
                
                result = self.file_manager.move_file(
                    source=operation.destination,
                    destination=operation.source
                )
                
                if result.success:
                    self.logger.info(f"Restored: {operation.destination.name} → {operation.source.parent.name}/")
                    stats["restored"] += 1
                else:
                    self.logger.error(f"Failed to restore file '{operation.destination.name}'")
                    stats["errors"] += 1
            except Exception as e:
                self.logger.error(f"Undo operation error: {str(e)}")
                stats["errors"] += 1
        
        for folder in folders_to_check:
            try:
                if folder.exists() and self._is_empty_directory(folder):
                    folder.rmdir()
                    self.logger.info(f"Deleted: Empty folder '{folder.name}/'")
                    stats["folders_removed"] += 1
            except Exception as e:
                self.logger.warning(f"Could not remove folder '{folder.name}': {str(e)}")
        
        self.history.mark_undo_complete()
        self._created_folders.clear()
        
        self.logger.separator()
        self.logger.success(f"Undo Complete: Restored {stats['restored']} file(s)")
        if stats["folders_removed"] > 0:
            self.logger.info(f"Cleanup: Removed {stats['folders_removed']} empty folder(s)")
        if stats["errors"] > 0:
            self.logger.warning(f"Encountered {stats['errors']} error(s) during undo operation")
        self.logger.separator()
        
        return stats

    
    def _create_recovery_backup(
        self,
        source_path: Path,
        destination_path: Path,
        files: List[Path],
        categories: List[FileCategory]
    ) -> Path | None:
        """Create a full recovery backup with actual file copies before organizing
        
        Creates a backup folder with actual file copies and metadata JSON.
        This provides true disaster recovery - files can be restored even if 
        corrupted, deleted by antivirus, or lost after organization.
        
        Args:
            source_path: Source directory
            destination_path: Destination directory  
            files: List of files to process
            categories: Active categories
            
        Returns:
            Path to recovery folder, or None if backup failed or disabled
        """
        # Check if recovery backup is enabled
        if self.config and not self.config.get("enable_recovery_backup", True):
            return None
            
        try:
            import shutil
            
            # Get custom recovery folder or use default
            if self.config:
                recovery_dir_str = self.config.get("recovery_backup_folder", str(Path.home() / "FileOrganizer_Recovery"))
                recovery_base = Path(recovery_dir_str).expanduser().resolve()
            else:
                recovery_base = Path.home() / "FileOrganizer_Recovery"
            
            recovery_base.mkdir(parents=True, exist_ok=True)
            
            # Get retention days from config
            retention_days = self.config.get("recovery_backup_retention_days", 30) if self.config else 30
            
            # Clean up old backups
            self._cleanup_old_backups(recovery_base, days=retention_days)
            
            # Get size limit from config
            max_backup_size_gb = self.config.get("recovery_backup_size_limit_gb", 5.0) if self.config else 5.0
            
            # Check available storage space
            available_space_gb = self._get_available_space_gb(recovery_base)
            if available_space_gb < max_backup_size_gb:
                self.logger.warning(f"Low disk space: {available_space_gb:.2f}GB available, need {max_backup_size_gb:.2f}GB")
                # Use whatever space is available (minus 1GB buffer for safety)
                max_backup_size_gb = max(0.1, available_space_gb - 1.0)
                self.logger.info(f"Adjusted backup size limit to {max_backup_size_gb:.2f}GB")
            
            # Create timestamped backup folder
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_folder = recovery_base / f"backup_{timestamp}"
            backup_folder.mkdir(parents=True, exist_ok=True)
            
            # Create files subfolder to store actual file copies
            files_backup_dir = backup_folder / "files"
            files_backup_dir.mkdir(exist_ok=True)
            
            self.logger.info(f"Creating full backup with file copies...")
            
            # Build recovery data and copy files
            recovery_data = {
                "timestamp": timestamp,
                "source": str(source_path),
                "destination": str(destination_path),
                "categories": [cat.name for cat in categories],
                "total_files": len(files),
                "backup_type": "full",
                "files": []
            }
            
            # Copy actual files and record metadata (limit to prevent disk overflow)
            files_copied = 0
            files_skipped = 0
            total_size_bytes = 0
            max_backup_size_bytes = int(max_backup_size_gb * 1024 * 1024 * 1024)
            
            for file_path in files[:1000]:  # Limit to first 1000 files
                try:
                    # Check backup size limit
                    if total_size_bytes > max_backup_size_bytes:
                        self.logger.warning(f"Backup size limit reached ({max_backup_size_gb:.1f}GB), skipping remaining files")
                        files_skipped = len(files) - files_copied
                        break
                    
                    category = self.file_service.get_file_category(file_path)
                    if category and file_path.exists():
                        # Copy file to backup folder with unique name
                        backup_filename = f"{files_copied}_{file_path.name}"
                        backup_file_path = files_backup_dir / backup_filename
                        
                        # Copy the actual file
                        shutil.copy2(file_path, backup_file_path)
                        file_size = file_path.stat().st_size
                        total_size_bytes += file_size
                        
                        dest_folder = destination_path / category.value
                        dest_file = dest_folder / file_path.name
                        
                        recovery_data["files"].append({
                            "original": str(file_path),
                            "destination": str(dest_file),
                            "category": category.value,
                            "backup_filename": backup_filename,
                            "file_size": file_size
                        })
                        files_copied += 1
                        
                except Exception as e:
                    self.logger.debug(f"Failed to backup file: {file_path.name}, error: {str(e)}")
                    files_skipped += 1
                    continue
            
            # Add summary info
            recovery_data["backup_size_bytes"] = total_size_bytes
            recovery_data["backup_size_mb"] = round(total_size_bytes / (1024 * 1024), 2)
            recovery_data["files_backed_up"] = files_copied
            recovery_data["files_skipped"] = files_skipped
            
            self.logger.info(f"Backed up {files_copied} files ({recovery_data['backup_size_mb']:.2f} MB)")
            if files_skipped > 0:
                self.logger.warning(f"Skipped {files_skipped} files during backup")
            
            # Save metadata JSON
            metadata_file = backup_folder / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(recovery_data, f, indent=2, ensure_ascii=False)
            
            # Create README in backup folder
            readme_file = backup_folder / "README.txt"
            readme_content = f"""FileOrganizer Full Backup - {timestamp}
========================================

This folder contains a complete backup of files before organization.

Backup Details:
- Files backed up: {files_copied}
- Backup size: {recovery_data['backup_size_mb']:.2f} MB
- Source: {source_path}
- Destination: {destination_path}

Contents:
- metadata.json: Information about all backed up files
- files/: Folder containing actual file copies

How to restore:
1. Use the Recovery Manager in the app (recommended)
2. Or manually: Files in the 'files/' folder can be copied back

Note: This backup will be automatically deleted after 30 days.
"""
            readme_file.write_text(readme_content, encoding='utf-8')
            
            return backup_folder
            
        except Exception as e:
            self.logger.warning(f"Failed to create recovery backup: {str(e)}")
            return None

    def _cleanup_old_backups(self, recovery_folder: Path, days: int = 30) -> None:
        """Delete backup folders older than specified days.
        
        Args:
            recovery_folder: Path to recovery backups folder
            days: Number of days to keep backups (default 30)
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0
            
            # Find all backup folders
            for backup_dir in recovery_folder.glob("backup_*"):
                if backup_dir.is_dir():
                    try:
                        # Extract timestamp from folder name
                        timestamp_str = backup_dir.name.replace("backup_", "")
                        backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                        
                        # Delete if older than cutoff
                        if backup_date < cutoff_date:
                            import shutil
                            shutil.rmtree(backup_dir)
                            deleted_count += 1
                            self.logger.debug(f"Deleted old backup: {backup_dir.name}")
                    except Exception:
                        # Skip if we can't parse date or delete fails
                        continue
            
            # Also clean up old JSON files (legacy format)
            for json_file in recovery_folder.glob("recovery_*.json"):
                try:
                    timestamp_str = json_file.stem.replace("recovery_", "")
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    if backup_date < cutoff_date:
                        json_file.unlink()
                        deleted_count += 1
                except Exception:
                    continue
            
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old backup(s) older than {days} days")
                
        except Exception as e:
            self.logger.debug(f"Backup cleanup failed: {str(e)}")

    def _get_available_space_gb(self, path: Path) -> float:
        """Get available disk space in GB for the given path.
        
        Args:
            path: Path to check disk space for
            
        Returns:
            Available space in GB
        """
        try:
            import shutil
            stat = shutil.disk_usage(path)
            return stat.free / (1024 * 1024 * 1024)  # Convert bytes to GB
        except Exception as e:
            self.logger.debug(f"Could not check disk space: {str(e)}")
            return 100.0  # Return large default if check fails


    @staticmethod
    def _is_empty_directory(path: Path) -> bool:
        """Check if directory is empty
        
        Args:
            path: Directory path to check
            
        Returns:
            True if directory is empty, False otherwise
        """
        try:
            return path.is_dir() and not any(path.iterdir())
        except Exception:
            return False
    
    @staticmethod
    def _passes_size_filter(file_path: Path, min_size_kb: float, max_size_kb: float) -> bool:
        """Check if file passes size filter criteria.
        
        Args:
            file_path: Path to file
            min_size_kb: Minimum size in KB (0 = no minimum)
            max_size_kb: Maximum size in KB (0 = no maximum)
            
        Returns:
            True if file passes filter, False otherwise
        """
        try:
            file_size_kb = file_path.stat().st_size / 1024
            
            # Check minimum
            if min_size_kb > 0 and file_size_kb < min_size_kb:
                return False
            
            # Check maximum
            if max_size_kb > 0 and file_size_kb > max_size_kb:
                return False
            
            return True
        except Exception:
            # If we can't get file size, include the file
            return True


    def create_jeff_su_framework(
        self,
        destination_path: Path,
    ) -> bool:
        """Create Jeff Su framework folder structure with READMEs
        
        Args:
            destination_path: Where to create the framework
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self._validate_destination_path(destination_path)
            self.logger.separator()
            self.logger.info("Creating Jeff Su Framework...")


            folder_names = list(JEFF_SU_STRUCTURE.keys())
            result = self.file_manager.create_folders(destination_path, folder_names)
            
            if not result.success:
                raise FileOperationError(f"Failed to create folders: {result.error}")


            for folder_name, info in JEFF_SU_STRUCTURE.items():
                folder_path = destination_path / folder_name
                readme_content = self._generate_readme(folder_name, info)
                readme_result = self.file_manager.write_readme(folder_path, readme_content)
                
                if readme_result.success:
                    self.logger.info(f"✓ {folder_name}/")
                else:
                    self.logger.warning(f"⚠ {folder_name}/ (README creation failed)")


            self.logger.success("Framework created successfully!")
            self.logger.separator()
            return True


        except Exception as e:
            self.logger.error(f"Failed to create framework: {str(e)}")
            return False


    @staticmethod
    def _generate_readme(folder_name: str, info: Dict[str, str]) -> str:
        """Generate README content for framework folder
        
        Args:
            folder_name: Name of the folder
            info: Folder metadata (description, keywords)
            
        Returns:
            README content string
        """
        return f"""JEFF SU FILE MANAGEMENT FRAMEWORK
        ═══════════════════════════════════════════════════



        Folder: {folder_name}
        Description: {info['description']}
        Keywords: {info['keywords']}



        This folder is part of Jeff Su's File Management Framework.
        Windows CLI Compatible (no brackets [ ])



        PRINCIPLES:
        ──────────────────────────────────────────────────
        • Organize by WHERE YOU USE it
        • Maximum 5 folder levels
        • Use consistent naming conventions
        • Keep files searchable and descriptive
        • Archive quarterly



        ═══════════════════════════════════════════════════
        """


    def _log_completion_stats(self, stats: OrganizationStats) -> None:
        """Log final organization statistics
        
        Args:
            stats: Organization statistics to log
        """
        self.logger.separator()
        self.logger.success("Organization Process Complete!")
        self.logger.info(f"Files Moved: {stats.moved}")
        self.logger.info(f"Files Skipped: {stats.skipped}")
        if stats.errors > 0:
            self.logger.error(f"Errors Encountered: {stats.errors}")
        self.logger.separator()
