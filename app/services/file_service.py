from pathlib import Path
from typing import Dict, List
from app.core.constants import FileCategory, FILE_EXTENSIONS, CUSTOM_CATEGORIES



class FileService:
    """Determines file categories by extension with custom category support"""
    
    def __init__(self, extensions_map: Dict[FileCategory, List[str]] | None = None) -> None:
        """Initialize file service
        
        Args:
            extensions_map: Custom extension mappings for testing
        """
        self.extensions_map = extensions_map or FILE_EXTENSIONS


    @staticmethod
    def get_file_extension(file_path: Path) -> str:
        """Get normalized file extension
        
        Args:
            file_path: Path to file
            
        Returns:
            File extension (lowercase, without dot)
        """
        return file_path.suffix.lower().lstrip(".")


    def get_file_category(self, file_path: Path) -> FileCategory | str:
        """Determine file category by extension
        
        Checks custom categories first, then default categories.
        
        Args:
            file_path: Path to file
            
        Returns:
            FileCategory enum or custom category name (str)
        """
        extension = self.get_file_extension(file_path)

        # Check custom categories first (higher priority)
        for category_name, extensions in CUSTOM_CATEGORIES.items():
            if extension in extensions:
                return category_name

        # Check default categories
        for category, extensions in self.extensions_map.items():
            if extension in extensions:
                return category

        return FileCategory.OTHERS


    def is_hidden_file(self, file_path: Path) -> bool:
        """Check if file is hidden (starts with dot)
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is hidden
        """
        return file_path.name.startswith(".")


    def get_file_size_mb(self, file_path: Path) -> float:
        """Get file size in megabytes
        
        Args:
            file_path: Path to file
            
        Returns:
            File size in MB
        """
        if not file_path.exists():
            return 0.0
        return file_path.stat().st_size / (1024 * 1024)


    def get_category_for_extension(self, extension: str) -> FileCategory | str | None:
        """Get category for a specific extension
        
        Args:
            extension: File extension (with or without dot)
            
        Returns:
            Category or None if not found
        """
        extension = extension.lower().lstrip(".")


        # Check custom categories first
        for category_name, extensions in CUSTOM_CATEGORIES.items():
            if extension in extensions:
                return category_name


        # Check default categories
        for category, extensions in self.extensions_map.items():
            if extension in extensions:
                return category


        return None
