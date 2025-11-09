from enum import Enum
from typing import Dict, List, Final


class FileCategory(Enum):
    """File categories enumeration - used for organization."""
    IMAGES = "Images"
    VIDEOS = "Videos"
    MUSIC = "Music"
    DOCUMENTS = "Documents"
    ARCHIVES = "Archives"
    PROGRAMS = "Programs"
    CODE = "Code"
    OTHERS = "Others"

    @property
    def folder_name(self) -> str:
        """Get human-readable folder name."""
        return self.value


class JeffSuFolders(Enum):
    """Jeff Su Framework folder structure.
    
    Numbered prefixes keep folders in consistent order across systems.
    """
    PERSONAL = "01_Personal"
    WORK = "02_Work"
    TEMPLATES = "03_Templates"
    TEMP_SHARE = "04_Temp_Share"
    ARCHIVE = "05_Archive"

    @property
    def folder_path(self) -> str:
        """Get folder path string."""
        return self.value


# Maps extensions to categories for automated sorting
FILE_EXTENSIONS: Final[Dict[FileCategory, List[str]]] = {
    FileCategory.IMAGES: [
        "jpg", "jpeg", "png", "gif", "bmp", "svg", "ico", "webp", "tiff", "heic"
    ],
    FileCategory.VIDEOS: [
        "mp4", "mkv", "mov", "avi", "wmv", "flv", "webm", "m4v", "3gp"
    ],
    FileCategory.MUSIC: [
        "mp3", "wav", "flac", "aac", "ogg", "wma", "m4a", "alac", "ape"
    ],
    FileCategory.DOCUMENTS: [
        "pdf", "doc", "docx", "txt", "rtf", "odt",
        "xls", "xlsx", "ppt", "pptx", "csv", "json", "md"
    ],
    FileCategory.ARCHIVES: [
        "zip", "rar", "7z", "tar", "gz", "bz2", "iso", "dmg"
    ],
    FileCategory.PROGRAMS: [
        "exe", "msi", "apk", "dmg", "deb", "pkg", "bin"
    ],
    FileCategory.CODE: [
        "py", "js", "html", "css", "cpp", "c", "java",
        "json", "xml", "sql", "sh", "bat", "go", "rs", "ts", "jsx"
    ],
}

# Keywords will power AI categorization when added; descriptions show up in UI
JEFF_SU_STRUCTURE: Final[Dict[str, Dict[str, str]]] = {
    JeffSuFolders.PERSONAL.value: {
        "keywords": "personal,private,me,my,hobby",
        "description": "Personal files (family, hobbies, personal projects)"
    },
    JeffSuFolders.WORK.value: {
        "keywords": "work,job,project,client,business",
        "description": "Work-related files and projects"
    },
    JeffSuFolders.TEMPLATES.value: {
        "keywords": "template,model,sample,boilerplate",
        "description": "Reusable templates and samples for quick starts"
    },
    JeffSuFolders.TEMP_SHARE.value: {
        "keywords": "temp,share,quick,draft,temporary",
        "description": "Temporary and shared files (clean quarterly)"
    },
    JeffSuFolders.ARCHIVE.value: {
        "keywords": "archive,old,backup,historical",
        "description": "Archived and old files (reference only)"
    },
}

# Application metadata
APP_NAME: Final[str] = "File Organizer Pro"
APP_VERSION: Final[str] = "2.0.0"
APP_DESCRIPTION: Final[str] = "Professional file organization with Jeff Su Framework"

# Configuration file location
CONFIG_FILENAME: Final[str] = ".file_organizer_config.json"
CONFIG_DIR: Final[str] = "~/.config/file_organizer"
