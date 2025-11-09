from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
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
    """Orchestrate file organization by category.
    
    Delegates to specialized services; doesn't handle file I/O directly.
    """
    
    def __init__(
        self,
        logger: LoggerService,
        file_service: FileService | None = None,
        file_manager: FileManager | None = None,
    ) -> None:
        """Initialize file organizer with dependency injection."""
        self.logger = logger
        self.file_service = file_service or FileService()
        self.file_manager = file_manager or FileManager(logger)
        self.history = OperationHistory()
        self._created_folders: Set[Path] = set()


    def preview_organization(
        self,
        source_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory] | None = None,
    ) -> Dict:
        """Preview files that will be organized without moving them.
        
        Args:
            source_path: Source folder path
            destination_path: Destination folder path
            active_categories: Categories to organize
            
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
            'files': []
        }
        
        for file_path in files:
            category = self.file_service.get_file_category(file_path)
            
            # Include file if category is active or OTHERS
            if category in categories or category == FileCategory.OTHERS:
                preview_data['total'] += 1
                
                # Count by category
                cat_name = category.value
                preview_data['summary'][cat_name] = preview_data['summary'].get(cat_name, 0) + 1
                
                # Add file details
                preview_data['files'].append({
                    'name': file_path.name,
                    'current': str(file_path.parent),
                    'category': cat_name
                })
        
        return preview_data


    def organize_folder(
        self,
        source_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory] | None = None,
    ) -> Dict[str, int]:
        """Organize files from source to destination by category.
        
        Now recursively scans nested folders and removes empty dirs after moving.
        """
        try:
            self.history.start_batch()
            self._created_folders.clear()
            
            validated_source = self._validate_source_path(source_path)
            validated_dest = self._validate_destination_path(destination_path)
            categories = self._validate_categories(active_categories)


            self.logger.separator()
            self.logger.info("Starting file organization")
            self.logger.info(f"Source: {validated_source}")
            self.logger.info(f"Destination: {validated_dest}")
            self.logger.info(f"Categories: {len(categories)} active")
            self.logger.separator()


            # Now scans nested folders recursively
            files = self.file_manager.get_files_in_folder(validated_source, recursive=True)
            if not files:
                self.logger.warning("No files found in source folder")
                return OrganizationStats().to_dict()


            self.logger.info(f"Found {len(files)} files to organize")


            stats = self._process_files(files, validated_dest, categories)


            # Clean up empty folders after moving all files
            folders_removed = self.file_manager.cleanup_empty_folders(validated_source)
            if folders_removed > 0:
                self.logger.info(f"Removed {folders_removed} empty folders")


            self._log_completion_stats(stats)
            return stats.to_dict()


        except FileOperationError as e:
            self.logger.error(f"File operation failed: {str(e)}")
            raise OrganizationError(f"File operation error: {str(e)}") from e
        except Exception as e:
            self.logger.error(f"Organization failed: {str(e)}")
            raise OrganizationError(f"Failed to organize files: {str(e)}") from e


    def _validate_source_path(self, source_path: Path) -> Path:
        """Validate source path exists and is a directory."""
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
        """Validate destination path; create if doesn't exist."""
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
        """Validate active categories; default to all except OTHERS."""
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
    ) -> OrganizationStats:
        """Process each file and accumulate statistics."""
        stats = OrganizationStats()


        for file_path in files:
            try:
                result = self._organize_file(file_path, destination_path, categories)
                if result == "moved":
                    stats.moved += 1
                elif result == "skipped":
                    stats.skipped += 1


            except Exception as e:
                self.logger.error(f"Failed to organize {file_path.name}: {str(e)}")
                stats.errors += 1


        return stats


    def _organize_file(
        self,
        file_path: Path,
        destination_path: Path,
        active_categories: List[FileCategory],
    ) -> str:
        """Move single file to its category folder."""
        category = self.file_service.get_file_category(file_path)


        if category not in active_categories and category != FileCategory.OTHERS:
            self.logger.debug(f"⊘ {file_path.name} (category inactive)")
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
            
            self.logger.info(f"✓ {file_path.name} → {category.value}/")
            return "moved"
        else:
            raise FileOperationError(f"Failed to move {file_path.name}: {result.error}")


    def undo_last_operation(self) -> Dict[str, int]:
        """Undo the last organize operation and clean up empty folders."""
        if not self.history.can_undo():
            raise OrganizationError("No operations to undo")
        
        batch = self.history.get_undo_batch()
        if not batch:
            raise OrganizationError("No operations to undo")
        
        self.logger.separator()
        self.logger.info(f"Undoing {len(batch)} file operations...")
        
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
                    self.logger.info(f"↩ {operation.destination.name} → {operation.source.parent.name}/")
                    stats["restored"] += 1
                else:
                    self.logger.error(f"Failed to restore {operation.destination.name}")
                    stats["errors"] += 1
            except Exception as e:
                self.logger.error(f"Undo error: {str(e)}")
                stats["errors"] += 1
        
        for folder in folders_to_check:
            try:
                if folder.exists() and self._is_empty_directory(folder):
                    folder.rmdir()
                    self.logger.info(f"🗑 Removed empty folder: {folder.name}/")
                    stats["folders_removed"] += 1
            except Exception as e:
                self.logger.warning(f"Could not remove folder {folder.name}: {str(e)}")
        
        self.history.mark_undo_complete()
        self._created_folders.clear()
        
        self.logger.separator()
        self.logger.success(f"Undo complete! Restored {stats['restored']} files")
        if stats["folders_removed"] > 0:
            self.logger.info(f"Removed {stats['folders_removed']} empty folders")
        if stats["errors"] > 0:
            self.logger.warning(f"Errors during undo: {stats['errors']}")
        self.logger.separator()
        
        return stats


    @staticmethod
    def _is_empty_directory(path: Path) -> bool:
        """Check if directory is empty."""
        try:
            return path.is_dir() and not any(path.iterdir())
        except Exception:
            return False


    def create_jeff_su_framework(
        self,
        destination_path: Path,
    ) -> bool:
        """Create Jeff Su framework folder structure with READMEs."""
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
        """Generate README content for framework folder."""
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
        """Log final organization statistics."""
        self.logger.separator()
        self.logger.success("Organization complete!")
        self.logger.info(f"✓ Moved: {stats.moved}")
        self.logger.info(f"✗ Errors: {stats.errors}")
        self.logger.info(f"⊘ Skipped: {stats.skipped}")
        self.logger.separator()
