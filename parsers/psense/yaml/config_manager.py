"""
Configuration Manager for YAML Parser

Manages configuration settings for YAML parsing, validation, and processing.
"""

import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class YAMLConfigManager:
    """Manages configuration for YAML parsing operations."""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        self.config_file = Path(config_file) if config_file else None
        self.config = self._load_default_config()
        
        if self.config_file and self.config_file.exists():
            self._load_config_file()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration settings."""
        return {
            "parsing": {
                "allow_duplicate_keys": False,
                "preserve_quotes": True,
                "preserve_comments": True,
                "preserve_order": True,
                "safe_load": True,
                "encoding": "utf-8"
            },
            "validation": {
                "enable_schema_validation": True,
                "strict_mode": False,
                "allow_unknown_fields": True,
                "validate_required_fields": True
            },
            "processing": {
                "extract_metadata": True,
                "extract_schemas": True,
                "extract_examples": True,
                "extract_descriptions": True,
                "normalize_structure": True,
                "resolve_references": True
            },
            "output": {
                "include_source_info": True,
                "include_line_numbers": True,
                "include_comments": True,
                "format_output": True,
                "max_depth": 10
            },
            "error_handling": {
                "continue_on_error": True,
                "log_errors": True,
                "raise_on_critical": True,
                "max_errors": 100
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "yaml_parser.log"
            }
        }
    
    def _load_config_file(self):
        """Load configuration from file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                file_config = yaml.safe_load(f) or {}
                self._merge_config(file_config)
                logger.info(f"Loaded configuration from {self.config_file}")
        except Exception as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration with existing config."""
        def merge_dicts(base: Dict[str, Any], update: Dict[str, Any]):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dicts(base[key], value)
                else:
                    base[key] = value
        
        merge_dicts(self.config, new_config)
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a configuration setting by key (supports dot notation)."""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key: str, value: Any):
        """Set a configuration setting by key (supports dot notation)."""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_parsing_config(self) -> Dict[str, Any]:
        """Get parsing configuration."""
        return self.get_setting("parsing", {})
    
    def get_validation_config(self) -> Dict[str, Any]:
        """Get validation configuration."""
        return self.get_setting("validation", {})
    
    def get_processing_config(self) -> Dict[str, Any]:
        """Get processing configuration."""
        return self.get_setting("processing", {})
    
    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.get_setting("output", {})
    
    def get_error_handling_config(self) -> Dict[str, Any]:
        """Get error handling configuration."""
        return self.get_setting("error_handling", {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """Get logging configuration."""
        return self.get_setting("logging", {})
    
    def save_config(self, filepath: Optional[Union[str, Path]] = None):
        """Save current configuration to file."""
        save_path = Path(filepath) if filepath else self.config_file
        
        if not save_path:
            raise ValueError("No config file path specified")
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            logger.info(f"Configuration saved to {save_path}")
        except Exception as e:
            logger.error(f"Failed to save configuration to {save_path}: {e}")
            raise
    
    def validate_config(self) -> bool:
        """Validate the current configuration."""
        try:
            required_sections = ["parsing", "validation", "processing", "output", "error_handling", "logging"]
            
            for section in required_sections:
                if section not in self.config:
                    logger.error(f"Missing required configuration section: {section}")
                    return False
            
            # Validate specific settings
            if not isinstance(self.get_setting("output.max_depth"), int):
                logger.error("output.max_depth must be an integer")
                return False
            
            if not isinstance(self.get_setting("error_handling.max_errors"), int):
                logger.error("error_handling.max_errors must be an integer")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False 