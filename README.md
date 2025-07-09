

# DesktopMCP - Desktop Automation through Model Context Protocol

DesktopMCP connects AI assistants like Claude to your desktop, enabling intelligent automation of your PC through the Model Context Protocol (MCP). This integration allows AI to help you with everyday tasks like opening applications, managing files, browsing the web, and monitoring your system.

## 🚀 Features

- **Application Management**: Open and control applications like Blender, VS Code, browsers, calculators, and more
- **File Operations**: Move, copy, and organize files and directories with intelligent path handling
- **Web Automation**: Search the web, navigate to websites, and automate browser tasks
- **System Monitoring**: Get real-time system information including CPU, memory, disk usage, and running processes
- **Screenshot Capture**: Take desktop screenshots for documentation or troubleshooting
- **Command Execution**: Run system commands safely with timeout controls
- **Cross-Platform**: Works on Windows, macOS, and Linux

## 🛠 Components

The system consists of a single MCP server that provides desktop automation tools:

- **Desktop MCP Server** (`src/desktop_mcp/server.py`): A Python server implementing the Model Context Protocol with desktop automation capabilities

## 📦 Installation

### Prerequisites

- Python 3.10 or newer
- uv package manager (recommended for dependency management)

**Install uv:**

**MacOS:**
```bash
brew install uv
```

**Windows:**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
set Path=C:\Users\%USERNAME%\.local\bin;%Path%
```

**Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Claude Desktop Integration

Add the following to your Claude Desktop configuration (`claude_desktop_config.json`):

```json
{
    "mcpServers": {
        "desktop": {
            "command": "uvx",
            "args": [
                "desktop-mcp"
            ]
        }
    }
}
```

### Cursor Integration

For Cursor IDE integration, add to Settings > MCP:

**Global Server:**
```json
{
    "mcpServers": {
        "desktop": {
            "command": "uvx",
            "args": [
                "desktop-mcp"
            ]
        }
    }
}
```

**Windows Users:** Use this configuration instead:
```json
{
    "mcpServers": {
        "desktop": {
            "command": "cmd",
            "args": [
                "/c",
                "uvx",
                "desktop-mcp"
            ]
        }
    }
}
```

## 🎯 Usage

Once configured, you'll see a hammer icon with desktop automation tools in Claude or Cursor. Here are some example commands you can use:

### Application Management
- "Open Blender so I can start 3D modeling"
- "Launch VS Code with my project directory"
- "Open a web browser and navigate to GitHub"
- "Start the calculator application"

### File Operations
- "Move all my photos from Downloads to Pictures folder"
- "Copy this project folder to my backup drive"
- "Show me what's in my Documents directory"
- "Organize my desktop files by file type"

### Web Browsing
- "Search Google for Python tutorials"
- "Navigate to stackoverflow.com"
- "Open YouTube and search for Blender tutorials"

### System Monitoring
- "Show me my system's current performance stats"
- "List the programs using the most CPU"
- "Take a screenshot of my desktop"
- "Check how much disk space I have left"

### Command Execution
- "Run a git status command in my project directory"
- "Update my system packages"
- "Check my network connectivity"

## 🔧 Available Tools

### Core Tools

- **`open_application`**: Launch applications with optional command-line arguments
- **`move_files`**: Move files or directories to new locations
- **`copy_files`**: Copy files or directories with path validation
- **`list_directory_contents`**: Browse and inspect directory contents
- **`search_web`**: Search using Google, Bing, or DuckDuckGo
- **`navigate_to_website`**: Open specific URLs in a browser
- **`take_screenshot`**: Capture desktop screenshots
- **`get_system_information`**: View comprehensive system stats
- **`get_running_processes`**: Monitor active processes and resource usage
- **`execute_command`**: Run system commands with safety controls
- **`close_browser`**: Clean up browser instances

### Supported Applications

The tool recognizes many common applications across platforms:

**Development:** Blender, VS Code, terminals, text editors
**Browsers:** Chrome, Firefox, Safari, Edge
**System:** File managers, calculators, system utilities
**Custom:** Any installed application can be launched by name

## 🔒 Security & Safety

- **Command Timeout**: All system commands have a 30-second timeout
- **Path Validation**: File operations validate paths and create directories safely
- **Browser Management**: Automated cleanup of browser instances
- **Error Handling**: Comprehensive error handling and logging
- **Safe Defaults**: Conservative settings for automation features

## 🖥 Platform Support

### Windows
- Full support for native Windows applications
- PowerShell and CMD command execution
- Windows Explorer integration
- Start menu application launching

### macOS
- Native app launching through `open` command
- Finder integration
- Terminal and shell support
- System application access

### Linux
- Support for common Linux desktop environments
- Package manager integration
- Terminal emulator support
- File manager integration

## 🚨 Troubleshooting

### Common Issues

**Connection Problems:**
- Ensure the MCP server is properly configured in Claude/Cursor
- Check that uv is installed and accessible
- Verify Python 3.10+ is available

**Permission Errors:**
- Some system operations may require elevated permissions
- File operations need appropriate read/write access
- Web automation requires internet connectivity

**Application Launch Issues:**
- Verify applications are installed and in system PATH
- Check application names match expected formats
- Some applications may require specific arguments

### Debug Tips

1. Check the MCP server logs for detailed error messages
2. Test file paths manually to verify accessibility
3. Ensure applications are properly installed
4. Verify system resources are available

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- Additional application integrations
- Enhanced file operation capabilities
- More system monitoring features
- Cross-platform compatibility improvements
- Security enhancements

## ⚖️ License

MIT License - See LICENSE file for details

## 🔗 Related Projects

This project was inspired by and transformed from the original BlenderMCP project, expanding beyond 3D modeling to comprehensive desktop automation.

---

**Made with ❤️ for desktop automation and AI assistance**
