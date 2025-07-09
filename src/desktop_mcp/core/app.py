"""
Main Application Controller for Desktop MCP

This is the central orchestrator that coordinates all subsystems including
GUI, voice interface, plugin management, command parsing, and execution.
"""

import asyncio
import logging
import signal
import sys
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
import json
from datetime import datetime

from .plugin_manager import plugin_manager
from .command_parser import command_parser, ParsedCommand
from ..tools.base_tool import tool_registry, ToolResult
from ..utils.config import ConfigManager
from ..utils.logging import setup_logging

logger = logging.getLogger(__name__)


class DesktopMCPApp:
    """
    Main Desktop MCP Application Controller
    
    Coordinates all subsystems:
    - Plugin management and tool discovery
    - Command parsing and execution
    - GUI interface
    - Voice interface
    - API server
    - Configuration management
    - Logging and monitoring
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.load_config()
        
        # Setup logging based on config
        setup_logging(self.config.get("logging", {}))
        
        # Core components
        self.plugin_manager = plugin_manager
        self.command_parser = command_parser
        self.tool_registry = tool_registry
        
        # Interface components (initialized later)
        self.gui_app = None
        self.voice_interface = None
        self.hotkey_manager = None
        self.api_server = None
        
        # State management
        self.running = False
        self.interfaces_enabled = {
            "gui": self.config.get("interfaces", {}).get("gui", {}).get("enabled", True),
            "voice": self.config.get("interfaces", {}).get("voice", {}).get("enabled", False),
            "hotkeys": self.config.get("interfaces", {}).get("hotkeys", {}).get("enabled", True),
            "api": self.config.get("interfaces", {}).get("api", {}).get("enabled", False)
        }
        
        # Command execution queue
        self.command_queue = asyncio.Queue()
        self.execution_history: List[Dict[str, Any]] = []
        
        logger.info("Desktop MCP Application initialized")
    
    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize all subsystems
        
        Returns:
            Dict with initialization results
        """
        logger.info("Initializing Desktop MCP Application...")
        
        results = {
            "success": True,
            "plugins_loaded": 0,
            "tools_available": 0,
            "interfaces_started": [],
            "errors": []
        }
        
        try:
            # Initialize plugin system
            plugin_results = self.plugin_manager.discover_and_load_all()
            results["plugins_loaded"] = plugin_results["tools_loaded"] + plugin_results["plugins_loaded"]
            results["tools_available"] = len(self.tool_registry.tools)
            
            if plugin_results["errors"]:
                results["errors"].extend(plugin_results["errors"])
            
            logger.info(f"Loaded {results['plugins_loaded']} plugins with {results['tools_available']} tools")
            
            # Initialize interfaces based on configuration
            if self.interfaces_enabled["gui"]:
                try:
                    await self._initialize_gui()
                    results["interfaces_started"].append("gui")
                except Exception as e:
                    error_msg = f"Failed to initialize GUI: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            if self.interfaces_enabled["voice"]:
                try:
                    await self._initialize_voice()
                    results["interfaces_started"].append("voice")
                except Exception as e:
                    error_msg = f"Failed to initialize voice interface: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            if self.interfaces_enabled["hotkeys"]:
                try:
                    await self._initialize_hotkeys()
                    results["interfaces_started"].append("hotkeys")
                except Exception as e:
                    error_msg = f"Failed to initialize hotkeys: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            if self.interfaces_enabled["api"]:
                try:
                    await self._initialize_api()
                    results["interfaces_started"].append("api")
                except Exception as e:
                    error_msg = f"Failed to initialize API server: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            # Start command processing
            asyncio.create_task(self._process_commands())
            
            self.running = True
            logger.info("Desktop MCP Application initialization complete")
            
        except Exception as e:
            error_msg = f"Critical initialization error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            results["success"] = False
            results["errors"].append(error_msg)
        
        return results
    
    async def _initialize_gui(self):
        """Initialize the GUI interface"""
        try:
            from ..interfaces.gui.main_window import DesktopMCPMainWindow
            
            # Create GUI in a separate thread to avoid blocking
            def create_gui():
                import sys
                from PyQt5.QtWidgets import QApplication
                
                if not QApplication.instance():
                    app = QApplication(sys.argv)
                else:
                    app = QApplication.instance()
                
                self.gui_app = DesktopMCPMainWindow(self)
                self.gui_app.show()
                
                return app
            
            # Run GUI in separate thread
            gui_thread = threading.Thread(target=create_gui, daemon=True)
            gui_thread.start()
            
            logger.info("GUI interface initialized")
            
        except ImportError as e:
            logger.warning(f"GUI dependencies not available: {e}")
            raise
    
    async def _initialize_voice(self):
        """Initialize the voice interface"""
        try:
            from ..interfaces.voice.voice_commands import VoiceInterface
            
            voice_config = self.config.get("interfaces", {}).get("voice", {})
            self.voice_interface = VoiceInterface(
                app=self,
                config=voice_config
            )
            
            await self.voice_interface.initialize()
            logger.info("Voice interface initialized")
            
        except ImportError as e:
            logger.warning(f"Voice interface dependencies not available: {e}")
            raise
    
    async def _initialize_hotkeys(self):
        """Initialize the hotkey system"""
        try:
            from ..interfaces.hotkeys.hotkey_manager import HotkeyManager
            
            hotkey_config = self.config.get("interfaces", {}).get("hotkeys", {})
            self.hotkey_manager = HotkeyManager(
                app=self,
                config=hotkey_config
            )
            
            await self.hotkey_manager.initialize()
            logger.info("Hotkey system initialized")
            
        except ImportError as e:
            logger.warning(f"Hotkey system dependencies not available: {e}")
            raise
    
    async def _initialize_api(self):
        """Initialize the API server"""
        try:
            from ..api.server import APIServer
            
            api_config = self.config.get("interfaces", {}).get("api", {})
            self.api_server = APIServer(
                app=self,
                config=api_config
            )
            
            await self.api_server.start()
            logger.info("API server initialized")
            
        except ImportError as e:
            logger.warning(f"API server dependencies not available: {e}")
            raise
    
    async def execute_command(self, command: str, source: str = "unknown") -> Dict[str, Any]:
        """
        Execute a natural language command
        
        Args:
            command: Natural language command string
            source: Source of the command (gui, voice, api, etc.)
            
        Returns:
            Dict with execution results
        """
        execution_id = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        logger.info(f"Executing command [{execution_id}] from {source}: {command}")
        
        try:
            # Parse the command
            parsed_command = self.command_parser.parse_command(command)
            
            if parsed_command.confidence < 0.3:
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "error": "Could not understand command",
                    "suggestions": parsed_command.alternatives or [],
                    "parsed_command": parsed_command
                }
            
            # Execute the tool if found
            if parsed_command.tool_name:
                tool = self.tool_registry.get_tool(parsed_command.tool_name)
                if tool:
                    # Use parsed parameters or fallback to empty dict
                    parameters = parsed_command.parameters or {}
                    
                    result = tool.safe_execute(**parameters)
                    
                    # Record the execution
                    execution_record = {
                        "execution_id": execution_id,
                        "timestamp": datetime.now().isoformat(),
                        "source": source,
                        "original_command": command,
                        "parsed_command": parsed_command,
                        "tool_name": parsed_command.tool_name,
                        "parameters": parameters,
                        "result": result,
                        "success": result.success
                    }
                    
                    self.execution_history.append(execution_record)
                    
                    # Remember successful command
                    if result.success:
                        self.command_parser.remember_command(parsed_command)
                    
                    logger.info(f"Command execution [{execution_id}] completed: {result.success}")
                    
                    return {
                        "success": result.success,
                        "execution_id": execution_id,
                        "result": result.to_dict(),
                        "parsed_command": parsed_command
                    }
                else:
                    return {
                        "success": False,
                        "execution_id": execution_id,
                        "error": f"Tool not found: {parsed_command.tool_name}",
                        "parsed_command": parsed_command
                    }
            else:
                return {
                    "success": False,
                    "execution_id": execution_id,
                    "error": "No tool identified for command",
                    "parsed_command": parsed_command
                }
        
        except Exception as e:
            error_msg = f"Command execution failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            return {
                "success": False,
                "execution_id": execution_id,
                "error": error_msg,
                "parsed_command": None
            }
    
    async def _process_commands(self):
        """Process commands from the queue"""
        while self.running:
            try:
                # Check for queued commands
                if not self.command_queue.empty():
                    command_data = await self.command_queue.get()
                    result = await self.execute_command(
                        command_data["command"],
                        command_data.get("source", "queue")
                    )
                    
                    # Handle result if callback provided
                    if "callback" in command_data and callable(command_data["callback"]):
                        command_data["callback"](result)
                
                # Small delay to prevent busy waiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in command processing: {e}")
                await asyncio.sleep(1)  # Longer delay on error
    
    async def queue_command(self, command: str, source: str = "queue", callback=None):
        """Queue a command for execution"""
        await self.command_queue.put({
            "command": command,
            "source": source,
            "callback": callback
        })
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of all available tools"""
        tools = []
        for tool_name, tool in self.tool_registry.tools.items():
            tools.append({
                "name": tool.metadata.name,
                "description": tool.metadata.description,
                "category": tool.metadata.category.value,
                "version": tool.metadata.version,
                "author": tool.metadata.author,
                "keywords": tool.metadata.keywords,
                "parameters": [
                    {
                        "name": param.name,
                        "type": param.type.value,
                        "description": param.description,
                        "required": param.required,
                        "default": param.default
                    }
                    for param in tool.metadata.parameters
                ]
            })
        return tools
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent command execution history"""
        return self.execution_history[-limit:]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "running": self.running,
            "tools_loaded": len(self.tool_registry.tools),
            "interfaces_enabled": self.interfaces_enabled,
            "recent_executions": len(self.execution_history),
            "plugin_info": self.plugin_manager.get_plugin_info(),
            "config": self.config
        }
    
    async def shutdown(self):
        """Gracefully shutdown the application"""
        logger.info("Shutting down Desktop MCP Application...")
        
        self.running = False
        
        # Shutdown interfaces
        if self.api_server:
            await self.api_server.stop()
        
        if self.voice_interface:
            await self.voice_interface.shutdown()
        
        if self.hotkey_manager:
            await self.hotkey_manager.shutdown()
        
        if self.gui_app:
            try:
                self.gui_app.close()
            except:
                pass
        
        # Save configuration
        self.config_manager.save_config(self.config)
        
        logger.info("Desktop MCP Application shutdown complete")


def setup_signal_handlers(app: DesktopMCPApp):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, initiating shutdown...")
        asyncio.create_task(app.shutdown())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for Desktop MCP"""
    try:
        # Create and initialize the application
        app = DesktopMCPApp()
        
        # Setup signal handlers
        setup_signal_handlers(app)
        
        # Initialize all subsystems
        init_results = await app.initialize()
        
        if not init_results["success"]:
            logger.error("Failed to initialize Desktop MCP")
            for error in init_results["errors"]:
                logger.error(f"  - {error}")
            return 1
        
        logger.info("Desktop MCP started successfully")
        logger.info(f"Tools available: {init_results['tools_available']}")
        logger.info(f"Interfaces: {', '.join(init_results['interfaces_started'])}")
        
        # Keep the application running
        while app.running:
            await asyncio.sleep(1)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Critical error in main: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Run the application
    exit_code = asyncio.run(main())
    sys.exit(exit_code)