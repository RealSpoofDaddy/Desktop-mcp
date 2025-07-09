# desktop_mcp_server.py
from mcp.server.fastmcp import FastMCP, Context, Image
import subprocess
import json
import asyncio
import logging
import tempfile
import shutil
import os
import platform
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
import requests
import psutil
import pyautogui
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from PIL import Image as PILImage
import base64

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DesktopMCP")

# Disable PyAutoGUI failsafe for automation
pyautogui.FAILSAFE = False

# Create the MCP server
mcp = FastMCP(
    "DesktopMCP",
    description="Desktop automation through the Model Context Protocol - AI assistant for managing your PC"
)

class ApplicationManager:
    """Manages application launching and control"""
    
    @staticmethod
    def get_system_type():
        """Get the current operating system"""
        return platform.system().lower()
    
    @staticmethod
    def open_application(app_name: str, args: List[str] = None) -> Dict[str, Any]:
        """Open an application with optional arguments"""
        system = ApplicationManager.get_system_type()
        if args is None:
            args = []
        
        # Common application mappings
        app_mappings = {
            "windows": {
                "blender": ["blender.exe"],
                "vscode": ["code"],
                "code": ["code"],
                "visual studio code": ["code"],
                "notepad": ["notepad.exe"],
                "calculator": ["calc.exe"],
                "browser": ["start", "chrome"],
                "chrome": ["start", "chrome"],
                "firefox": ["start", "firefox"],
                "edge": ["start", "msedge"],
                "explorer": ["explorer.exe"],
                "cmd": ["cmd.exe"],
                "powershell": ["powershell.exe"],
                "terminal": ["cmd.exe"]
            },
            "darwin": {  # macOS
                "blender": ["open", "-a", "Blender"],
                "vscode": ["open", "-a", "Visual Studio Code"],
                "code": ["open", "-a", "Visual Studio Code"],
                "visual studio code": ["open", "-a", "Visual Studio Code"],
                "browser": ["open", "-a", "Google Chrome"],
                "chrome": ["open", "-a", "Google Chrome"],
                "firefox": ["open", "-a", "Firefox"],
                "safari": ["open", "-a", "Safari"],
                "finder": ["open", "-a", "Finder"],
                "terminal": ["open", "-a", "Terminal"],
                "calculator": ["open", "-a", "Calculator"]
            },
            "linux": {
                "blender": ["blender"],
                "vscode": ["code"],
                "code": ["code"],
                "visual studio code": ["code"],
                "browser": ["google-chrome"],
                "chrome": ["google-chrome"],
                "firefox": ["firefox"],
                "terminal": ["gnome-terminal"],
                "nautilus": ["nautilus"],
                "calculator": ["gnome-calculator"],
                "gedit": ["gedit"]
            }
        }
        
        try:
            app_lower = app_name.lower()
            if system in app_mappings and app_lower in app_mappings[system]:
                cmd = app_mappings[system][app_lower] + args
            else:
                # Try to run the app directly
                cmd = [app_name] + args
            
            logger.info(f"Opening application: {' '.join(cmd)}")
            
            if system == "windows" and cmd[0] == "start":
                # Use shell=True for Windows start command
                process = subprocess.Popen(cmd, shell=True)
            else:
                process = subprocess.Popen(cmd)
            
            return {
                "success": True,
                "message": f"Successfully opened {app_name}",
                "pid": process.pid,
                "command": ' '.join(cmd)
            }
        except Exception as e:
            logger.error(f"Failed to open application {app_name}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to open {app_name}"
            }

class FileManager:
    """Manages file operations"""
    
    @staticmethod
    def move_file(source: str, destination: str) -> Dict[str, Any]:
        """Move a file or directory from source to destination"""
        try:
            source_path = Path(source).expanduser().resolve()
            dest_path = Path(destination).expanduser().resolve()
            
            if not source_path.exists():
                return {"success": False, "error": f"Source path does not exist: {source_path}"}
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.is_file():
                shutil.move(str(source_path), str(dest_path))
            else:
                shutil.move(str(source_path), str(dest_path))
            
            return {
                "success": True,
                "message": f"Successfully moved {source_path} to {dest_path}",
                "source": str(source_path),
                "destination": str(dest_path)
            }
        except Exception as e:
            logger.error(f"Failed to move file: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def copy_file(source: str, destination: str) -> Dict[str, Any]:
        """Copy a file or directory from source to destination"""
        try:
            source_path = Path(source).expanduser().resolve()
            dest_path = Path(destination).expanduser().resolve()
            
            if not source_path.exists():
                return {"success": False, "error": f"Source path does not exist: {source_path}"}
            
            # Create destination directory if it doesn't exist
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            if source_path.is_file():
                shutil.copy2(str(source_path), str(dest_path))
            else:
                shutil.copytree(str(source_path), str(dest_path), dirs_exist_ok=True)
            
            return {
                "success": True,
                "message": f"Successfully copied {source_path} to {dest_path}",
                "source": str(source_path),
                "destination": str(dest_path)
            }
        except Exception as e:
            logger.error(f"Failed to copy file: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def list_directory(path: str) -> Dict[str, Any]:
        """List contents of a directory"""
        try:
            dir_path = Path(path).expanduser().resolve()
            
            if not dir_path.exists():
                return {"success": False, "error": f"Directory does not exist: {dir_path}"}
            
            if not dir_path.is_dir():
                return {"success": False, "error": f"Path is not a directory: {dir_path}"}
            
            contents = []
            for item in dir_path.iterdir():
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": item.stat().st_mtime
                }
                contents.append(item_info)
            
            return {
                "success": True,
                "path": str(dir_path),
                "contents": contents,
                "count": len(contents)
            }
        except Exception as e:
            logger.error(f"Failed to list directory: {str(e)}")
            return {"success": False, "error": str(e)}

class WebManager:
    """Manages web browsing and searching"""
    
    def __init__(self):
        self.driver = None
    
    def _get_driver(self):
        """Get or create a Chrome WebDriver instance"""
        if self.driver is None:
            try:
                chrome_options = Options()
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                # Don't run headless by default so user can see the browser
                # chrome_options.add_argument("--headless")
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Chrome WebDriver initialized")
            except Exception as e:
                logger.error(f"Failed to initialize WebDriver: {str(e)}")
                raise
        return self.driver
    
    def search_web(self, query: str, engine: str = "google") -> Dict[str, Any]:
        """Search the web using the specified search engine"""
        try:
            driver = self._get_driver()
            
            search_urls = {
                "google": f"https://www.google.com/search?q={query}",
                "bing": f"https://www.bing.com/search?q={query}",
                "duckduckgo": f"https://duckduckgo.com/?q={query}"
            }
            
            if engine.lower() not in search_urls:
                return {"success": False, "error": f"Unsupported search engine: {engine}"}
            
            url = search_urls[engine.lower()]
            driver.get(url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Get page title and current URL
            title = driver.title
            current_url = driver.current_url
            
            return {
                "success": True,
                "message": f"Successfully searched for '{query}' on {engine}",
                "query": query,
                "engine": engine,
                "title": title,
                "url": current_url
            }
        except Exception as e:
            logger.error(f"Failed to search web: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def navigate_to_url(self, url: str) -> Dict[str, Any]:
        """Navigate to a specific URL"""
        try:
            driver = self._get_driver()
            
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            driver.get(url)
            time.sleep(2)
            
            title = driver.title
            current_url = driver.current_url
            
            return {
                "success": True,
                "message": f"Successfully navigated to {url}",
                "title": title,
                "url": current_url
            }
        except Exception as e:
            logger.error(f"Failed to navigate to URL: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def close_browser(self):
        """Close the browser instance"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Browser closed")
                return {"success": True, "message": "Browser closed successfully"}
            except Exception as e:
                logger.error(f"Failed to close browser: {str(e)}")
                return {"success": False, "error": str(e)}
        return {"success": True, "message": "No browser instance to close"}

class SystemMonitor:
    """Monitors system resources and processes"""
    
    @staticmethod
    def get_system_info() -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            # CPU info
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Memory info
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk info
            disk_usage = psutil.disk_usage('/')
            
            # System info
            boot_time = psutil.boot_time()
            
            return {
                "success": True,
                "system": {
                    "platform": platform.platform(),
                    "architecture": platform.architecture(),
                    "processor": platform.processor(),
                    "boot_time": boot_time
                },
                "cpu": {
                    "usage_percent": cpu_percent,
                    "count": cpu_count,
                    "frequency": {
                        "current": cpu_freq.current if cpu_freq else None,
                        "min": cpu_freq.min if cpu_freq else None,
                        "max": cpu_freq.max if cpu_freq else None
                    }
                },
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "swap": {
                    "total": swap.total,
                    "used": swap.used,
                    "percent": swap.percent
                },
                "disk": {
                    "total": disk_usage.total,
                    "used": disk_usage.used,
                    "free": disk_usage.free,
                    "percent": (disk_usage.used / disk_usage.total) * 100
                }
            }
        except Exception as e:
            logger.error(f"Failed to get system info: {str(e)}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_running_processes() -> Dict[str, Any]:
        """Get list of running processes"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            return {
                "success": True,
                "processes": processes[:20],  # Top 20 processes
                "total_count": len(processes)
            }
        except Exception as e:
            logger.error(f"Failed to get running processes: {str(e)}")
            return {"success": False, "error": str(e)}

# Initialize managers
app_manager = ApplicationManager()
file_manager = FileManager()
web_manager = WebManager()
system_monitor = SystemMonitor()

# MCP Tools

@mcp.tool()
def open_application(ctx: Context, app_name: str, arguments: List[str] = None) -> str:
    """
    Open an application on the desktop.
    
    Parameters:
    - app_name: Name of the application to open (e.g., 'blender', 'vscode', 'chrome', 'calculator')
    - arguments: Optional list of command line arguments to pass to the application
    
    Supported applications include: Blender, VS Code, browsers (Chrome, Firefox), file managers, terminals, and more.
    """
    try:
        result = app_manager.open_application(app_name, arguments)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error opening application: {str(e)}")
        return f"Error opening application: {str(e)}"

@mcp.tool()
def move_files(ctx: Context, source_path: str, destination_path: str) -> str:
    """
    Move a file or directory from source to destination.
    
    Parameters:
    - source_path: Path to the file or directory to move
    - destination_path: Path where the file or directory should be moved
    
    Supports both relative and absolute paths. Creates destination directories if they don't exist.
    """
    try:
        result = file_manager.move_file(source_path, destination_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error moving file: {str(e)}")
        return f"Error moving file: {str(e)}"

@mcp.tool()
def copy_files(ctx: Context, source_path: str, destination_path: str) -> str:
    """
    Copy a file or directory from source to destination.
    
    Parameters:
    - source_path: Path to the file or directory to copy
    - destination_path: Path where the file or directory should be copied
    
    Supports both relative and absolute paths. Creates destination directories if they don't exist.
    """
    try:
        result = file_manager.copy_file(source_path, destination_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error copying file: {str(e)}")
        return f"Error copying file: {str(e)}"

@mcp.tool()
def list_directory_contents(ctx: Context, directory_path: str) -> str:
    """
    List the contents of a directory.
    
    Parameters:
    - directory_path: Path to the directory to list
    
    Returns information about files and subdirectories including names, types, sizes, and modification times.
    """
    try:
        result = file_manager.list_directory(directory_path)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error listing directory: {str(e)}")
        return f"Error listing directory: {str(e)}"

@mcp.tool()
def search_web(ctx: Context, query: str, search_engine: str = "google") -> str:
    """
    Search the web using the specified search engine.
    
    Parameters:
    - query: The search query to look for
    - search_engine: Search engine to use ('google', 'bing', 'duckduckgo')
    
    Opens a browser window and performs the search, returning information about the search results page.
    """
    try:
        result = web_manager.search_web(query, search_engine)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error searching web: {str(e)}")
        return f"Error searching web: {str(e)}"

@mcp.tool()
def navigate_to_website(ctx: Context, url: str) -> str:
    """
    Navigate to a specific website URL.
    
    Parameters:
    - url: The URL to navigate to (with or without http/https prefix)
    
    Opens a browser window and navigates to the specified URL.
    """
    try:
        result = web_manager.navigate_to_url(url)
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error navigating to website: {str(e)}")
        return f"Error navigating to website: {str(e)}"

@mcp.tool()
def take_screenshot(ctx: Context, save_path: str = None) -> Image:
    """
    Take a screenshot of the desktop.
    
    Parameters:
    - save_path: Optional path to save the screenshot file
    
    Returns the screenshot as an Image.
    """
    try:
        screenshot = pyautogui.screenshot()
        
        if save_path:
            screenshot.save(save_path)
            logger.info(f"Screenshot saved to {save_path}")
        
        # Convert to bytes for MCP Image
        import io
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        return Image(data=img_byte_arr, format="png")
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        raise Exception(f"Screenshot failed: {str(e)}")

@mcp.tool()
def get_system_information(ctx: Context) -> str:
    """
    Get comprehensive system information including CPU, memory, disk usage, and running processes.
    
    Returns detailed information about system resources and performance.
    """
    try:
        result = system_monitor.get_system_info()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return f"Error getting system info: {str(e)}"

@mcp.tool()
def get_running_processes(ctx: Context) -> str:
    """
    Get a list of currently running processes with CPU and memory usage.
    
    Returns the top 20 processes sorted by CPU usage.
    """
    try:
        result = system_monitor.get_running_processes()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error getting running processes: {str(e)}")
        return f"Error getting running processes: {str(e)}"

@mcp.tool()
def execute_command(ctx: Context, command: str, shell: bool = True) -> str:
    """
    Execute a system command.
    
    Parameters:
    - command: The command to execute
    - shell: Whether to run the command in a shell (default: True)
    
    WARNING: Use with caution as this can execute any system command.
    """
    try:
        logger.info(f"Executing command: {command}")
        
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout
        )
        
        return json.dumps({
            "success": True,
            "command": command,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }, indent=2)
        
    except subprocess.TimeoutExpired:
        return json.dumps({
            "success": False,
            "error": "Command timed out after 30 seconds",
            "command": command
        }, indent=2)
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "command": command
        }, indent=2)

@mcp.tool()
def close_browser(ctx: Context) -> str:
    """
    Close the browser instance that was opened for web operations.
    
    Use this to clean up browser windows opened by search_web or navigate_to_website.
    """
    try:
        result = web_manager.close_browser()
        return json.dumps(result, indent=2)
    except Exception as e:
        logger.error(f"Error closing browser: {str(e)}")
        return f"Error closing browser: {str(e)}"

def main():
    """Run the Desktop MCP server"""
    import mcp.server.stdio
    
    logger.info("Starting Desktop MCP Server")
    mcp.run()

if __name__ == "__main__":
    main()