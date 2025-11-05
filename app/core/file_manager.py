"""Low-level file operations with robust error handling."""
from dataclasses import dataclass
from enum import Enum
import shutil
from pathlib import Path
from typing import List
from app.services.logger_service import LoggerService


class FileOperationError(Exception):
    """Base exception for file operations"""
    pass


class FileNotFoundError(FileOperationError):
    """File does not exist"""
    pass


class PermissionDeniedError(FileOperationError):
    """No permission to perform operation"""
    pass


class DuplicateFileError(FileOperationError):
    """File already exists at destination"""
    pass


class DuplicateHandlingStrategy(Enum):
    """Strategy for handling duplicate filenames"""
    SKIP = "skip"
    REPLACE = "replace"
    RENAME = "rename"


@dataclass
class FileOperationResult:
    """Result of file operation with detailed status"""
    success: bool
    path: Path | None = None
    error: FileOperationError | None = None
    strategy_applied: DuplicateHandlingStrategy | None = None

    def raise_if_failed(self) -> None:
        """Raise exception if operation failed"""
        if not self.success and self.error:
            raise self.error


class FileManager:
    """Handle file operations (move, copy, create folders).
    
    All methods return FileOperationResult with detailed context instead of
    implicit booleans, enabling better error recovery for callers.
    """
    
    def __init__(
        self,
        logger: LoggerService,
        duplicate_strategy: DuplicateHandlingStrategy = DuplicateHandlingStrategy.RENAME,
    ) -> None:
        """Initialize file manager with dependency injection.
        
        Args:
            logger: LoggerService for logging
            duplicate_strategy: How to handle duplicate filenames
        """
        self.logger = logger
        self.duplicate_strategy = duplicate_strategy

    def move_file(
        self,
        source: Path,
        destination: Path,
        strategy: DuplicateHandlingStrategy | None = None,
    ) -> FileOperationResult:
        """Move file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            strategy: Override default duplicate strategy (optional)
            
        Returns:
            FileOperationResult with detailed status
        """
        strategy = strategy or self.duplicate_strategy

        try:
            if not source.exists():
                error = FileNotFoundError(f"Source not found: {source}")
                return FileOperationResult(success=False, error=error)

            if not source.is_file():
                error = FileOperationError(f"Source is not a file: {source}")
                return FileOperationResult(success=False, error=error)

            self._ensure_parent_directory(destination)

            final_destination = self._resolve_duplicate_path(destination, strategy)

            try:
                shutil.move(str(source), str(final_destination))
            except PermissionError as e:
                raise PermissionDeniedError(f"Permission denied: {str(e)}")
            except FileExistsError as e:
                raise DuplicateFileError(f"File exists: {final_destination}")
            except OSError as e:
                raise FileOperationError(f"OS error during move: {str(e)}")

            return FileOperationResult(
                success=True,
                path=final_destination,
                strategy_applied=strategy,
            )

        except FileOperationError as e:
            self.logger.error(f"File operation failed: {str(e)}")
            return FileOperationResult(success=False, error=e)
        except Exception as e:
            error = FileOperationError(f"Unexpected error moving {source.name}: {str(e)}")
            self.logger.error(str(error))
            return FileOperationResult(success=False, error=error)

    def copy_file(
        self,
        source: Path,
        destination: Path,
        strategy: DuplicateHandlingStrategy | None = None,
    ) -> FileOperationResult:
        """Copy file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
            strategy: Duplicate handling strategy
            
        Returns:
            FileOperationResult with detailed status
        """
        strategy = strategy or self.duplicate_strategy

        try:
            if not source.exists():
                error = FileNotFoundError(f"Source not found: {source}")
                return FileOperationResult(success=False, error=error)

            self._ensure_parent_directory(destination)

            final_destination = self._resolve_duplicate_path(destination, strategy)

            try:
                shutil.copy2(str(source), str(final_destination))
            except PermissionError as e:
                raise PermissionDeniedError(f"Permission denied: {str(e)}")
            except OSError as e:
                raise FileOperationError(f"OS error during copy: {str(e)}")

            return FileOperationResult(
                success=True,
                path=final_destination,
                strategy_applied=strategy,
            )

        except FileOperationError as e:
            self.logger.error(f"Copy failed: {str(e)}")
            return FileOperationResult(success=False, error=e)
        except Exception as e:
            error = FileOperationError(f"Unexpected error copying {source.name}: {str(e)}")
            self.logger.error(str(error))
            return FileOperationResult(success=False, error=error)

    def _ensure_parent_directory(self, file_path: Path) -> None:
        """Ensure parent directory exists, create if needed.
        
        Args:
            file_path: File path whose parent should exist
            
        Raises:
            FileOperationError: If directory creation fails
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        except PermissionError as e:
            raise PermissionDeniedError(f"Cannot create parent directory: {str(e)}")
        except OSError as e:
            raise FileOperationError(f"Cannot create parent directory: {str(e)}")

    def _resolve_duplicate_path(
        self,
        destination: Path,
        strategy: DuplicateHandlingStrategy,
    ) -> Path:
        """Apply duplicate handling strategy to destination path.
        
        Args:
            destination: Desired destination path
            strategy: How to handle existing file
            
        Returns:
            Final path (may be modified based on strategy)
            
        Raises:
            DuplicateFileError: If strategy is SKIP and file exists
        """
        if not destination.exists():
            return destination

        if strategy == DuplicateHandlingStrategy.SKIP:
            raise DuplicateFileError(f"File exists (skipping): {destination}")

        if strategy == DuplicateHandlingStrategy.REPLACE:
            return destination

        if strategy == DuplicateHandlingStrategy.RENAME:
            return self._generate_unique_path(destination)

        raise FileOperationError(f"Unknown strategy: {strategy}")

    def _generate_unique_path(self, path: Path) -> Path:
        """Generate unique filename by appending counter.
        
        Example: file.txt → file_1.txt → file_2.txt
        
        Args:
            path: Original file path
            
        Returns:
            Path with unique filename
        """
        stem = path.stem
        suffix = path.suffix
        parent = path.parent

        counter = 1
        while True:
            new_path = parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

            if counter > 10000:
                raise FileOperationError(f"Cannot generate unique path: {path}")

    def create_folders(self, base_path: Path, folder_names: List[str]) -> FileOperationResult:
        """Create multiple folders in base path.
        
        Args:
            base_path: Base path where folders will be created
            folder_names: List of folder names to create
            
        Returns:
            FileOperationResult with details
        """
        try:
            if not folder_names:
                raise FileOperationError("Folder list cannot be empty")

            for folder_name in folder_names:
                folder_path = base_path / folder_name
                try:
                    folder_path.mkdir(parents=True, exist_ok=True, mode=0o755)
                except PermissionError as e:
                    raise PermissionDeniedError(f"Cannot create {folder_name}: {str(e)}")
                except OSError as e:
                    raise FileOperationError(f"Cannot create {folder_name}: {str(e)}")

            return FileOperationResult(success=True, path=base_path)

        except FileOperationError as e:
            self.logger.error(f"Folder creation failed: {str(e)}")
            return FileOperationResult(success=False, error=e)
        except Exception as e:
            error = FileOperationError(f"Unexpected error creating folders: {str(e)}")
            self.logger.error(str(error))
            return FileOperationResult(success=False, error=error)

    def write_readme(
        self,
        folder_path: Path,
        content: str,
        overwrite: bool = False,
    ) -> FileOperationResult:
        """Write README file to folder with UTF-8 encoding.
        
        Args:
            folder_path: Path to folder
            content: README content
            overwrite: Whether to overwrite existing README
            
        Returns:
            FileOperationResult with status
        """
        try:
            readme_path = folder_path / "README.txt"

            if readme_path.exists() and not overwrite:
                self.logger.debug(f"README already exists: {readme_path}")
                return FileOperationResult(success=True, path=readme_path)

            try:
                with open(readme_path, "w", encoding="utf-8") as f:
                    f.write(content)
            except PermissionError as e:
                raise PermissionDeniedError(f"Cannot write README: {str(e)}")
            except IOError as e:
                raise FileOperationError(f"IO error writing README: {str(e)}")

            return FileOperationResult(success=True, path=readme_path)

        except FileOperationError as e:
            self.logger.error(f"README write failed: {str(e)}")
            return FileOperationResult(success=False, error=e)
        except Exception as e:
            error = FileOperationError(f"Unexpected error writing README: {str(e)}")
            self.logger.error(str(error))
            return FileOperationResult(success=False, error=error)

    def get_files_in_folder(self, folder_path: Path) -> List[Path]:
        """Get all files in folder (non-recursive, files only).
        
        Args:
            folder_path: Path to folder
            
        Returns:
            Sorted list of file paths
            
        Raises:
            FileOperationError: If folder cannot be read
        """
        try:
            if not folder_path.exists():
                raise FileNotFoundError(f"Folder not found: {folder_path}")

            if not folder_path.is_dir():
                raise FileOperationError(f"Path is not a directory: {folder_path}")

            files = [f for f in folder_path.iterdir() if f.is_file()]
            return sorted(files)

        except FileOperationError:
            raise
        except PermissionError as e:
            raise PermissionDeniedError(f"Permission denied: {folder_path}")
        except Exception as e:
            raise FileOperationError(f"Failed to read folder: {str(e)}")
