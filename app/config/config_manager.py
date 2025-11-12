import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from app.core.constants import add_custom_category, remove_custom_category, CUSTOM_CATEGORIES



class ConfigError(Exception):
    """Base configuration error"""
    pass



class ConfigValidationError(ConfigError):
    """Configuration validation failed"""
    pass



class ConfigIOError(ConfigError):
    """Configuration I/O operation failed"""
    pass



@dataclass
class ConfigSchema:
    """Define valid configuration keys, types, and validation rules"""
    key: str
    expected_type: type
    default: Any
    validator: Optional[Callable[[Any], bool]] = None
    description: str = ""


    def validate(self, value: Any) -> None:
        """Validate value against schema.
        
        Args:
            value: Value to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        # Type check
        if not isinstance(value, self.expected_type):
            raise ConfigValidationError(
                f"Invalid type for '{self.key}': expected {self.expected_type.__name__}, "
                f"got {type(value).__name__}"
            )


        # Custom validator
        if self.validator and not self.validator(value):
            raise ConfigValidationError(f"Validation failed for '{self.key}': {value}")



class ConfigManager:
    """Configuration management with validation and persistence.
    
    Loaded from file at init, changes tracked for atomic saves.
    """
    
    def __init__(
        self,
        config_file: Path,
        schema: Dict[str, ConfigSchema] | None = None,
    ) -> None:
        """Initialize config manager.
        
        Args:
            config_file: Path to JSON config file
            schema: Configuration schema for validation
        """
        self.config_file = config_file.expanduser().resolve()
        self.schema = schema or {}
        self._config: Dict[str, Any] = {}
        self._dirty = False
        self._load()
        self._load_custom_categories()


    def _load(self) -> None:
        """Load configuration from file or initialize with defaults.
        
        Raises:
            ConfigIOError: If file is corrupted and unreadable
        """
        self._config = {}


        # Load from file if exists
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                
                # Validate and load each key
                for key, value in loaded.items():
                    if key in self.schema:
                        try:
                            self.schema[key].validate(value)
                            self._config[key] = value
                        except ConfigValidationError:
                            # Skip invalid entries, use default
                            self._config[key] = self.schema[key].default
                    else:
                        # Allow unknown keys for forward compatibility
                        self._config[key] = value
            except json.JSONDecodeError as e:
                raise ConfigIOError(f"Config file corrupted (invalid JSON): {str(e)}")
            except IOError as e:
                raise ConfigIOError(f"Cannot read config file: {str(e)}")


        # Fill missing keys with defaults
        for key, schema in self.schema.items():
            if key not in self._config:
                self._config[key] = schema.default


    def _load_custom_categories(self) -> None:
        """Load custom categories from config into constants module."""
        custom_cats = self.get("custom_categories", {})
        for name, extensions in custom_cats.items():
            add_custom_category(name, extensions)


    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value safely.
        
        Args:
            key: Configuration key
            default: Fallback value if key not found
            
        Returns:
            Configuration value or default
        """
        return self._config.get(key, default)


    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Set configuration value with validation.
        
        Args:
            key: Configuration key
            value: Configuration value
            persist: Save to disk immediately (set False for batch updates)
            
        Raises:
            ConfigValidationError: If value fails validation
        """
        # Validate if schema exists
        if key in self.schema:
            self.schema[key].validate(value)


        self._config[key] = value
        self._dirty = True


        if persist:
            self.save()


    def save(self) -> None:
        """Persist configuration to file.
        
        Raises:
            ConfigIOError: If save fails
        """
        if not self._dirty:
            return


        try:
            # Ensure parent directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
            
            # Write atomically (write to temp, then rename)
            temp_file = self.config_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            temp_file.replace(self.config_file)
            
            self._dirty = False
        except IOError as e:
            raise ConfigIOError(f"Cannot save config: {str(e)}")


    def add_custom_category(self, name: str, extensions: list) -> None:
        """Add custom category to config and runtime.
        
        Args:
            name: Category name
            extensions: List of extensions (e.g., ["pdf", "doc"])
        """
        if "custom_categories" not in self._config:
            self._config["custom_categories"] = {}
        
        # Clean extensions (remove dots, lowercase)
        clean_exts = [ext.lower().lstrip('.') for ext in extensions]
        
        self._config["custom_categories"][name] = clean_exts
        add_custom_category(name, clean_exts)
        self._dirty = True
        self.save()


    def remove_custom_category(self, name: str) -> None:
        """Remove custom category from config and runtime.
        
        Args:
            name: Category name to remove
        """
        if "custom_categories" in self._config and name in self._config["custom_categories"]:
            del self._config["custom_categories"][name]
            remove_custom_category(name)
            self._dirty = True
            self.save()


    def get_custom_categories(self) -> Dict[str, list]:
        """Get all custom categories.
        
        Returns:
            Dictionary mapping category names to extension lists
        """
        return self._config.get("custom_categories", {})


    def get_all(self) -> Dict[str, Any]:
        """Get all configuration (immutable copy)"""
        return self._config.copy()


    def reset_to_defaults(self) -> None:
        """Reset all configuration to schema defaults"""
        for key, schema in self.schema.items():
            self._config[key] = schema.default
        self._dirty = True


    def has_key(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._config



# Default application configuration schema
DEFAULT_CONFIG_SCHEMA: Dict[str, ConfigSchema] = {
    "destination_folder": ConfigSchema(
        key="destination_folder",
        expected_type=str,
        default=str(Path.home() / "Downloads"),
        validator=lambda v: Path(v).expanduser().parent.exists(),
        description="Default folder for organized files"
    ),
    "theme": ConfigSchema(
        key="theme",
        expected_type=str,
        default="dark",
        validator=lambda v: v in ["light", "dark"],
        description="Application theme (light or dark)"
    ),
    "auto_organize_on_startup": ConfigSchema(
        key="auto_organize_on_startup",
        expected_type=bool,
        default=False,
        description="Automatically organize files when app starts"
    ),
    "remember_last_source": ConfigSchema(
        key="remember_last_source",
        expected_type=bool,
        default=True,
        description="Remember last used source folder"
    ),
    "last_source_folder": ConfigSchema(
        key="last_source_folder",
        expected_type=str,
        default="",
        description="Last used source folder path"
    ),
    "last_destination_folder": ConfigSchema(
        key="last_destination_folder",
        expected_type=str,
        default="",
        description="Last used destination folder path"
    ),
    "auto_save_paths": ConfigSchema(
        key="auto_save_paths",
        expected_type=bool,
        default=True,
        description="Auto-save last used folder paths"
    ),
    "custom_categories": ConfigSchema(
        key="custom_categories",
        expected_type=dict,
        default={},
        description="User-defined custom file categories"
    ),
    "duplicate_handling": ConfigSchema(
    key="duplicate_handling",
    expected_type=str,
    default="rename",
    validator=lambda v: v in ["skip", "rename", "replace"],
    description="How to handle duplicate files (skip, rename, replace)"
    ),
    "min_file_size_kb": ConfigSchema(
        key="min_file_size_kb",
        expected_type=(int, float),
        default=0,
        validator=lambda v: v >= 0,
        description="Minimum file size in KB (0 = no minimum)"
    ),
    "max_file_size_kb": ConfigSchema(
        key="max_file_size_kb",
        expected_type=(int, float),
        default=0,
        validator=lambda v: v >= 0,
        description="Maximum file size in KB (0 = no maximum)"
    ),
    "enable_size_filter": ConfigSchema(
        key="enable_size_filter",
        expected_type=bool,
        default=False,
        description="Enable file size filtering"
    ),
    "log_export_directory": ConfigSchema(
        key="log_export_directory",
        expected_type=str,
        default=str(Path.home()),
        description="Default directory for exporting activity logs"
    ),
}
