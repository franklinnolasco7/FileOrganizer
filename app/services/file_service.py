from pathlib import Path
from typing import Dict, List
from app.core.constants import FileCategory, FILE_EXTENSIONS


class FileService:
    """Determines file categories by extension.
    
    Only handles categorization logic; FileManager handles actual file operations.
    """
    
    def __init__(self, extensions_map: Dict[FileCategory, List[str]] | None = None) -> None:
        """Initialize file service with extension mappings.
        
        Args:
            extensions_map: Custom file extension mappings (testability)
        """
        self.extensions_map = extensions_map or FILE_EXTENSIONS

    @staticmethod
    def get_file_extension(file_path: Path) -> str:
        """Get file extension without dot.
        
        Args:
            file_path: Path to file
            
        Returns:
            File extension (lowercase, without dot)
        """
        return file_path.suffix.lower().lstrip(".")

    def get_file_category(self, file_path: Path) -> FileCategory:
        """Determine file category by extension.
        
        Args:
            file_path: Path to file
            
        Returns:
            FileCategory enum value
        """
        extension = self.get_file_extension(file_path)

        for category, extensions in self.extensions_map.items():
            if extension in extensions:
                return category

        return FileCategory.OTHERS

    def is_hidden_file(self, file_path: Path) -> bool:
        """Check if file is hidden (starts with dot on Unix).
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is hidden
        """
        return file_path.name.startswith(".")

    def get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in megabytes.
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in MB
        """
        if not file_path.exists():
            return 0.0
        return file_path.stat().st_size / (1024 * 1024)
