"""
Plugin Manager for Desktop MCP

Handles discovery, loading, and management of tools and plugins.
Supports both built-in tools and external plugins with hot-reload capabilities.
"""

import os
import sys
import importlib
import importlib.util
import inspect
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import traceback
import json
from dataclasses import asdict

from ..tools.base_tool import BaseTool, ToolRegistry, tool_registry

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    
    Supports:
    - Auto-discovery of tools in the tools directory
    - Loading external plugins from the plugins directory
    - Hot-reload for development
    - Dependency checking and management
    """
    
    def __init__(self, tools_dir: Optional[Path] = None, plugins_dir: Optional[Path] = None):
        self.tools_dir = tools_dir or Path(__file__).parent.parent / "tools"
        self.plugins_dir = plugins_dir or Path.cwd() / "plugins"
        self.registry = tool_registry
        self.loaded_modules: Dict[str, Any] = {}
        self.plugin_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Ensure directories exist
        self.tools_dir.mkdir(exist_ok=True)
        self.plugins_dir.mkdir(exist_ok=True)
        
        logger.info(f"Plugin manager initialized")
        logger.info(f"Tools directory: {self.tools_dir}")
        logger.info(f"Plugins directory: {self.plugins_dir}")
    
    def discover_and_load_all(self) -> Dict[str, Any]:
        """
        Discover and load all available tools and plugins.
        
        Returns:
            Dict with loading results and statistics
        """
        results = {
            "tools_loaded": 0,
            "plugins_loaded": 0,
            "errors": [],
            "tools": [],
            "plugins": []
        }
        
        try:
            # Load built-in tools
            tools_result = self._load_tools_from_directory(self.tools_dir)
            results["tools_loaded"] = tools_result["loaded"]
            results["tools"] = tools_result["tools"]
            results["errors"].extend(tools_result["errors"])
            
            # Load external plugins
            plugins_result = self._load_plugins_from_directory(self.plugins_dir)
            results["plugins_loaded"] = plugins_result["loaded"]
            results["plugins"] = plugins_result["plugins"]
            results["errors"].extend(plugins_result["errors"])
            
            total_loaded = results["tools_loaded"] + results["plugins_loaded"]
            logger.info(f"Plugin discovery complete: {total_loaded} total tools loaded")
            
        except Exception as e:
            error_msg = f"Plugin discovery failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results["errors"].append(error_msg)
        
        return results
    
    def _load_tools_from_directory(self, directory: Path) -> Dict[str, Any]:
        """Load tools from a directory recursively"""
        results = {
            "loaded": 0,
            "tools": [],
            "errors": []
        }
        
        if not directory.exists():
            logger.warning(f"Tools directory does not exist: {directory}")
            return results
        
        # Find all Python files in the directory
        python_files = list(directory.rglob("*.py"))
        python_files = [f for f in python_files if not f.name.startswith("__")]
        
        for py_file in python_files:
            try:
                tools = self._load_tools_from_file(py_file)
                results["loaded"] += len(tools)
                results["tools"].extend(tools)
                
            except Exception as e:
                error_msg = f"Failed to load tools from {py_file}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    def _load_plugins_from_directory(self, directory: Path) -> Dict[str, Any]:
        """Load external plugins from directory"""
        results = {
            "loaded": 0,
            "plugins": [],
            "errors": []
        }
        
        if not directory.exists():
            logger.warning(f"Plugins directory does not exist: {directory}")
            return results
        
        # Look for plugin directories (each plugin should be in its own directory)
        for plugin_dir in directory.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue
            
            try:
                plugin_info = self._load_plugin_from_directory(plugin_dir)
                if plugin_info:
                    results["loaded"] += plugin_info["tools_count"]
                    results["plugins"].append(plugin_info)
                    
            except Exception as e:
                error_msg = f"Failed to load plugin from {plugin_dir}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
        
        return results
    
    def _load_plugin_from_directory(self, plugin_dir: Path) -> Optional[Dict[str, Any]]:
        """Load a plugin from its directory"""
        # Look for plugin metadata
        metadata_file = plugin_dir / "plugin.json"
        plugin_info = {
            "name": plugin_dir.name,
            "directory": str(plugin_dir),
            "tools_count": 0,
            "metadata": {}
        }
        
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    plugin_info["metadata"] = json.load(f)
                logger.info(f"Loaded plugin metadata: {plugin_info['metadata']}")
            except Exception as e:
                logger.warning(f"Failed to load plugin metadata from {metadata_file}: {e}")
        
        # Look for main plugin file
        main_file = plugin_dir / "__init__.py"
        if not main_file.exists():
            main_file = plugin_dir / "main.py"
        
        if not main_file.exists():
            # Look for any Python files
            python_files = list(plugin_dir.glob("*.py"))
            if not python_files:
                logger.warning(f"No Python files found in plugin directory: {plugin_dir}")
                return None
            main_file = python_files[0]
        
        # Load tools from the main file
        try:
            tools = self._load_tools_from_file(main_file)
            plugin_info["tools_count"] = len(tools)
            
            if tools:
                logger.info(f"Loaded plugin '{plugin_info['name']}' with {len(tools)} tools")
                return plugin_info
            else:
                logger.warning(f"No tools found in plugin: {plugin_dir}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load tools from plugin {plugin_dir}: {e}")
            raise
    
    def _load_tools_from_file(self, file_path: Path) -> List[str]:
        """Load tools from a Python file"""
        tools_loaded = []
        
        try:
            # Create module spec
            module_name = f"desktop_mcp_plugin_{file_path.stem}_{id(file_path)}"
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load module spec from {file_path}")
            
            # Load the module
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            
            # Store the loaded module
            self.loaded_modules[str(file_path)] = module
            
            # Find all tool classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseTool) and 
                    obj is not BaseTool):
                    
                    try:
                        # Instantiate and register the tool
                        tool_instance = obj()
                        self.registry.register(tool_instance)
                        tools_loaded.append(tool_instance.metadata.name)
                        
                        logger.info(f"Loaded tool: {tool_instance.metadata.name} from {file_path}")
                        
                    except Exception as e:
                        logger.error(f"Failed to instantiate tool {name} from {file_path}: {e}")
            
        except Exception as e:
            logger.error(f"Failed to load module from {file_path}: {e}")
            logger.debug(traceback.format_exc())
            raise
        
        return tools_loaded
    
    def reload_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """
        Reload a specific plugin (useful for development).
        
        Args:
            plugin_path: Path to the plugin file or directory
            
        Returns:
            Dict with reload results
        """
        result = {
            "success": False,
            "tools_reloaded": 0,
            "error": None
        }
        
        try:
            path = Path(plugin_path)
            
            # Remove old tools from registry
            if str(path) in self.loaded_modules:
                # Find tools that came from this module and remove them
                old_module = self.loaded_modules[str(path)]
                tools_to_remove = []
                
                for tool_name, tool in self.registry.tools.items():
                    if tool.__class__.__module__ == old_module.__name__:
                        tools_to_remove.append(tool_name)
                
                for tool_name in tools_to_remove:
                    del self.registry.tools[tool_name]
                    logger.info(f"Removed old tool: {tool_name}")
                
                # Remove module from sys.modules
                if old_module.__name__ in sys.modules:
                    del sys.modules[old_module.__name__]
                
                del self.loaded_modules[str(path)]
            
            # Reload the plugin
            if path.is_file():
                tools = self._load_tools_from_file(path)
                result["tools_reloaded"] = len(tools)
            elif path.is_dir():
                plugin_info = self._load_plugin_from_directory(path)
                result["tools_reloaded"] = plugin_info["tools_count"] if plugin_info else 0
            else:
                raise FileNotFoundError(f"Plugin path not found: {plugin_path}")
            
            result["success"] = True
            logger.info(f"Successfully reloaded plugin: {plugin_path}")
            
        except Exception as e:
            error_msg = f"Failed to reload plugin {plugin_path}: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
        
        return result
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Get information about all loaded plugins"""
        return {
            "total_tools": len(self.registry.tools),
            "categories": {
                category.value: len(tools) 
                for category, tools in self.registry.categories.items()
            },
            "tools_by_category": {
                category.value: [
                    {
                        "name": tool.metadata.name,
                        "description": tool.metadata.description,
                        "version": tool.metadata.version,
                        "author": tool.metadata.author
                    }
                    for tool in self.registry.get_tools_by_category(category)
                ]
                for category in self.registry.categories.keys()
            },
            "loaded_modules": list(self.loaded_modules.keys()),
            "plugin_metadata": self.plugin_metadata
        }
    
    def validate_plugin_dependencies(self, tool: BaseTool) -> Dict[str, Any]:
        """
        Validate that a tool's dependencies are satisfied.
        
        Args:
            tool: Tool to validate
            
        Returns:
            Dict with validation results
        """
        result = {
            "valid": True,
            "missing_packages": [],
            "platform_compatible": True,
            "python_version_ok": True
        }
        
        try:
            # Check Python packages
            for package in tool.metadata.requirements:
                try:
                    importlib.import_module(package)
                except ImportError:
                    result["missing_packages"].append(package)
                    result["valid"] = False
            
            # Check platform compatibility
            import platform
            current_platform = platform.system().lower()
            if current_platform not in tool.metadata.platforms:
                result["platform_compatible"] = False
                result["valid"] = False
            
            # Check Python version
            import sys
            current_version = sys.version_info
            required_version = tuple(map(int, tool.metadata.min_python_version.split('.')))
            
            if current_version < required_version:
                result["python_version_ok"] = False
                result["valid"] = False
                
        except Exception as e:
            logger.error(f"Error validating dependencies for {tool.metadata.name}: {e}")
            result["valid"] = False
            result["error"] = str(e)
        
        return result
    
    def install_missing_dependencies(self, tool: BaseTool) -> Dict[str, Any]:
        """
        Attempt to install missing dependencies for a tool.
        
        Args:
            tool: Tool to install dependencies for
            
        Returns:
            Dict with installation results
        """
        result = {
            "success": False,
            "installed": [],
            "failed": [],
            "error": None
        }
        
        try:
            validation = self.validate_plugin_dependencies(tool)
            
            if validation["missing_packages"]:
                import subprocess
                
                for package in validation["missing_packages"]:
                    try:
                        # Try to install the package
                        subprocess.check_call([
                            sys.executable, "-m", "pip", "install", package
                        ])
                        result["installed"].append(package)
                        logger.info(f"Successfully installed package: {package}")
                        
                    except subprocess.CalledProcessError as e:
                        result["failed"].append(package)
                        logger.error(f"Failed to install package {package}: {e}")
                
                result["success"] = len(result["failed"]) == 0
            else:
                result["success"] = True
                
        except Exception as e:
            error_msg = f"Error installing dependencies: {str(e)}"
            logger.error(error_msg)
            result["error"] = error_msg
        
        return result
    
    def create_plugin_template(self, plugin_name: str, output_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Create a template for a new plugin.
        
        Args:
            plugin_name: Name of the new plugin
            output_dir: Directory to create the plugin in (defaults to plugins_dir)
            
        Returns:
            Dict with creation results
        """
        if output_dir is None:
            output_dir = self.plugins_dir
        
        plugin_dir = output_dir / plugin_name
        
        try:
            plugin_dir.mkdir(exist_ok=True)
            
            # Create plugin metadata
            metadata = {
                "name": plugin_name,
                "version": "1.0.0",
                "description": f"Custom plugin: {plugin_name}",
                "author": "Desktop MCP User",
                "requirements": []
            }
            
            with open(plugin_dir / "plugin.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create main plugin file
            template_code = f'''"""
{plugin_name} Plugin for Desktop MCP

This is a template plugin. Modify it to create your custom tools.
"""

from desktop_mcp.tools.base_tool import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult, 
    ToolCategory, ParameterType
)


class {plugin_name.title()}Tool(BaseTool):
    """Example tool for {plugin_name} plugin"""
    
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="{plugin_name}_example",
            description="Example tool from {plugin_name} plugin",
            category=ToolCategory.CUSTOM,
            version="1.0.0",
            parameters=[
                ToolParameter(
                    name="message",
                    type=ParameterType.STRING,
                    description="Message to process",
                    required=True
                )
            ],
            keywords=["{plugin_name}", "example", "template"],
            examples=[
                "Process a simple message"
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        message = kwargs.get("message", "")
        
        result_message = f"Processed message: {{message}}"
        
        return ToolResult(
            success=True,
            message=result_message,
            data={{"processed_message": result_message, "original": message}}
        )


# The tool will be automatically discovered and loaded
'''
            
            with open(plugin_dir / "__init__.py", 'w') as f:
                f.write(template_code)
            
            # Create README
            readme_content = f"""# {plugin_name} Plugin

This is a custom plugin for Desktop MCP.

## Installation

Place this directory in your Desktop MCP plugins folder.

## Usage

The plugin will be automatically discovered and loaded.

## Development

Modify the `__init__.py` file to add your custom tools.
"""
            
            with open(plugin_dir / "README.md", 'w') as f:
                f.write(readme_content)
            
            return {
                "success": True,
                "plugin_dir": str(plugin_dir),
                "files_created": ["plugin.json", "__init__.py", "README.md"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Global plugin manager instance
plugin_manager = PluginManager()