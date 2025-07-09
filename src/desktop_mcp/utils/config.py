"""
Configuration Management for Desktop MCP

Handles loading, saving, and managing configuration files with support for
hierarchical configs, environment variables, and validation.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager for Desktop MCP
    
    Features:
    - JSON and YAML configuration support
    - Environment variable substitution
    - Hierarchical configuration (system > user > profile)
    - Configuration validation
    - Backup and restore
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / "data" / "configs" / "main.json"
        self.config_dir = self.config_path.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Default configuration
        self.default_config = {
            "version": "2.0.0",
            "app_name": "Desktop MCP",
            "debug": False,
            
            "logging": {
                "level": "INFO",
                "file": "data/logs/desktop_mcp.log",
                "max_size": "10MB",
                "backup_count": 5,
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            
            "interfaces": {
                "gui": {
                    "enabled": True,
                    "theme": "dark",
                    "window_size": [1200, 800],
                    "window_position": "center",
                    "auto_start": True
                },
                "voice": {
                    "enabled": False,
                    "engine": "whisper",  # whisper, vosk, google
                    "wake_word": "desktop",
                    "language": "en-US",
                    "confidence_threshold": 0.7,
                    "continuous_listening": False
                },
                "hotkeys": {
                    "enabled": True,
                    "global_hotkey": "ctrl+shift+d",
                    "screenshot_hotkey": "ctrl+shift+s",
                    "voice_toggle": "ctrl+shift+v"
                },
                "api": {
                    "enabled": False,
                    "host": "localhost",
                    "port": 8000,
                    "cors_enabled": True,
                    "auth_required": False
                }
            },
            
            "plugins": {
                "auto_discovery": True,
                "auto_install_dependencies": False,
                "plugin_directories": ["plugins", "~/.desktop_mcp/plugins"],
                "disabled_plugins": []
            },
            
            "system": {
                "startup_check": True,
                "auto_update": False,
                "telemetry": False,
                "crash_reporting": True
            },
            
            "profiles": {
                "default": "general",
                "available": ["general", "development", "creative", "productivity"]
            }
        }
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file
        
        Returns:
            Dict with configuration data
        """
        try:
            if self.config_path.exists():
                logger.info(f"Loading configuration from {self.config_path}")
                
                with open(self.config_path, 'r') as f:
                    if self.config_path.suffix.lower() == '.yaml':
                        config = yaml.safe_load(f)
                    else:
                        config = json.load(f)
                
                # Merge with defaults
                merged_config = self._merge_configs(self.default_config, config)
                
                # Substitute environment variables
                merged_config = self._substitute_env_vars(merged_config)
                
                logger.info("Configuration loaded successfully")
                return merged_config
            else:
                logger.info("No configuration file found, using defaults")
                return self.default_config.copy()
                
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            logger.info("Using default configuration")
            return self.default_config.copy()
    
    def save_config(self, config: Dict[str, Any]):
        """
        Save configuration to file
        
        Args:
            config: Configuration dictionary to save
        """
        try:
            # Create backup of existing config
            if self.config_path.exists():
                backup_path = self.config_path.with_suffix(
                    f'.backup.{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
                )
                self.config_path.rename(backup_path)
                logger.info(f"Created configuration backup: {backup_path}")
            
            # Save new configuration
            with open(self.config_path, 'w') as f:
                if self.config_path.suffix.lower() == '.yaml':
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge user config with default config
        
        Args:
            default: Default configuration
            user: User configuration
            
        Returns:
            Merged configuration
        """
        merged = default.copy()
        
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        
        return merged
    
    def _substitute_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Substitute environment variables in configuration values
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables substituted
        """
        def substitute_value(value: Any) -> Any:
            if isinstance(value, str):
                # Replace ${VAR} or $VAR patterns
                import re
                pattern = r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)'
                
                def replace_match(match):
                    var_name = match.group(1) or match.group(2)
                    return os.getenv(var_name, match.group(0))
                
                return re.sub(pattern, replace_match, value)
            elif isinstance(value, dict):
                return {k: substitute_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [substitute_value(item) for item in value]
            else:
                return value
        
        result = substitute_value(config)
        return result if isinstance(result, dict) else config
    
    def get_profile_config(self, profile_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific profile
        
        Args:
            profile_name: Name of the profile
            
        Returns:
            Profile configuration
        """
        profile_path = self.config_dir / "profiles" / f"{profile_name}.json"
        
        if profile_path.exists():
            try:
                with open(profile_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load profile {profile_name}: {e}")
        
        return {}
    
    def save_profile_config(self, profile_name: str, config: Dict[str, Any]):
        """
        Save configuration for a specific profile
        
        Args:
            profile_name: Name of the profile
            config: Profile configuration
        """
        profile_dir = self.config_dir / "profiles"
        profile_dir.mkdir(exist_ok=True)
        
        profile_path = profile_dir / f"{profile_name}.json"
        
        try:
            with open(profile_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Profile {profile_name} saved")
        except Exception as e:
            logger.error(f"Failed to save profile {profile_name}: {e}")
    
    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate configuration and return validation results
        
        Args:
            config: Configuration to validate
            
        Returns:
            Dict with validation results
        """
        results = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Check required fields
            required_fields = ["version", "app_name"]
            for field in required_fields:
                if field not in config:
                    results["errors"].append(f"Missing required field: {field}")
                    results["valid"] = False
            
            # Validate interfaces
            if "interfaces" in config:
                interfaces = config["interfaces"]
                
                # Validate GUI config
                if "gui" in interfaces:
                    gui_config = interfaces["gui"]
                    if "window_size" in gui_config:
                        size = gui_config["window_size"]
                        if not isinstance(size, list) or len(size) != 2:
                            results["errors"].append("GUI window_size must be [width, height]")
                            results["valid"] = False
                
                # Validate API config
                if "api" in interfaces:
                    api_config = interfaces["api"]
                    if "port" in api_config:
                        port = api_config["port"]
                        if not isinstance(port, int) or port < 1 or port > 65535:
                            results["errors"].append("API port must be between 1 and 65535")
                            results["valid"] = False
            
            # Check for deprecated fields
            deprecated_fields = []  # Add any deprecated fields here
            for field in deprecated_fields:
                if field in config:
                    results["warnings"].append(f"Deprecated field: {field}")
            
        except Exception as e:
            results["errors"].append(f"Configuration validation error: {str(e)}")
            results["valid"] = False
        
        return results
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.save_config(self.default_config)
        logger.info("Configuration reset to defaults")
    
    def export_config(self, export_path: Path):
        """
        Export current configuration to a file
        
        Args:
            export_path: Path to export the configuration to
        """
        try:
            config = self.load_config()
            
            with open(export_path, 'w') as f:
                if export_path.suffix.lower() == '.yaml':
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Configuration exported to {export_path}")
            
        except Exception as e:
            logger.error(f"Failed to export configuration: {e}")
    
    def import_config(self, import_path: Path):
        """
        Import configuration from a file
        
        Args:
            import_path: Path to import the configuration from
        """
        try:
            with open(import_path, 'r') as f:
                if import_path.suffix.lower() == '.yaml':
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)
            
            # Validate imported config
            validation = self.validate_config(config)
            if not validation["valid"]:
                raise ValueError(f"Invalid configuration: {validation['errors']}")
            
            self.save_config(config)
            logger.info(f"Configuration imported from {import_path}")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise