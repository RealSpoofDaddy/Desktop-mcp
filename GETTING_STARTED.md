# Getting Started with Desktop MCP 2.0

## 🚀 Quick Start Guide

### Installation

1. **Install Dependencies**
   ```bash
   pip install -e .
   ```

2. **Install Optional Dependencies** (for full functionality)
   ```bash
   # For NLP features
   pip install spacy
   python -m spacy download en_core_web_sm
   
   # For advanced features
   pip install -e ".[llm,advanced]"
   ```

### Basic Usage

#### 1. **Command Line Interface**
```bash
# Start the core application
desktop-mcp

# Run CLI version (current MCP server)
desktop-mcp-cli
```

#### 2. **Python API Usage**
```python
from desktop_mcp.core.app import DesktopMCPApp
import asyncio

async def main():
    app = DesktopMCPApp()
    await app.initialize()
    
    # Execute a command
    result = await app.execute_command("take screenshot")
    print(result)

asyncio.run(main())
```

#### 3. **Creating Custom Tools**

Create a new tool by extending `BaseTool`:

```python
# plugins/my_plugin/__init__.py
from desktop_mcp.tools.base_tool import (
    BaseTool, ToolMetadata, ToolParameter, ToolResult,
    ToolCategory, ParameterType
)

class GreetingTool(BaseTool):
    def get_metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="greeting_tool",
            description="Generate personalized greetings",
            category=ToolCategory.UTILITIES,
            parameters=[
                ToolParameter(
                    name="name",
                    type=ParameterType.STRING,
                    description="Name to greet",
                    required=True
                ),
                ToolParameter(
                    name="style",
                    type=ParameterType.STRING,
                    description="Greeting style",
                    required=False,
                    default="friendly",
                    choices=["friendly", "formal", "casual"]
                )
            ]
        )
    
    def execute(self, **kwargs) -> ToolResult:
        name = kwargs.get("name")
        style = kwargs.get("style", "friendly")
        
        greetings = {
            "friendly": f"Hello there, {name}! Hope you're having a great day!",
            "formal": f"Good day, {name}. I trust you are well.",
            "casual": f"Hey {name}! What's up?"
        }
        
        message = greetings.get(style, greetings["friendly"])
        
        return ToolResult(
            success=True,
            message=message,
            data={"greeting": message, "name": name, "style": style}
        )
```

#### 4. **Using Natural Language Commands**

```python
from desktop_mcp.core.command_parser import command_parser

# Parse natural language
parsed = command_parser.parse_command("greet John in a formal style")
print(f"Tool: {parsed.tool_name}")
print(f"Parameters: {parsed.parameters}")
```

### Configuration

Create a configuration file at `data/configs/main.json`:

```json
{
  "version": "2.0.0",
  "debug": true,
  "interfaces": {
    "gui": {
      "enabled": true,
      "theme": "dark"
    },
    "voice": {
      "enabled": false,
      "engine": "whisper"
    },
    "hotkeys": {
      "enabled": true,
      "global_hotkey": "ctrl+shift+d"
    }
  },
  "logging": {
    "level": "DEBUG",
    "console_enabled": true
  }
}
```

### Development Workflow

1. **Plugin Development**
   ```bash
   # Create plugin template
   python -c "
   from desktop_mcp.core.plugin_manager import plugin_manager
   plugin_manager.create_plugin_template('my_plugin')
   "
   ```

2. **Hot Reload During Development**
   ```python
   # Reload a specific plugin
   result = plugin_manager.reload_plugin("plugins/my_plugin")
   print(result)
   ```

3. **Testing Commands**
   ```python
   from desktop_mcp.core.app import DesktopMCPApp
   
   app = DesktopMCPApp()
   result = await app.execute_command("your command here")
   print(result)
   ```

### Available Commands (Examples)

Based on existing patterns, these commands should work:

- `"take screenshot"` - Capture screen
- `"open blender"` - Launch application
- `"search for python tutorials"` - Web search
- `"copy file.txt to backup"` - File operations
- `"check system status"` - System monitoring

### Debugging

1. **Enable Debug Logging**
   ```python
   import logging
   logging.getLogger().setLevel(logging.DEBUG)
   ```

2. **Check Plugin Loading**
   ```python
   from desktop_mcp.core.plugin_manager import plugin_manager
   info = plugin_manager.get_plugin_info()
   print(info)
   ```

3. **View Command Parsing**
   ```python
   from desktop_mcp.core.command_parser import command_parser
   parsed = command_parser.parse_command("your command")
   print(f"Confidence: {parsed.confidence}")
   print(f"Intent: {parsed.intent}")
   print(f"Action: {parsed.action}")
   ```

### Next Steps for Development

1. **Implement GUI** - The main user interface
2. **Migrate Existing Tools** - Convert current MCP tools
3. **Add Voice Interface** - Speech recognition
4. **Create Profiles** - User-specific configurations

### Troubleshooting

**Plugin Not Loading?**
- Check file is in `plugins/` or `src/desktop_mcp/tools/`
- Verify tool inherits from `BaseTool`
- Check logs in `data/logs/desktop_mcp.log`

**Command Not Recognized?**
- Add custom patterns to command parser
- Check tool name and keywords
- Verify tool is registered in registry

**Import Errors?**
- Install missing dependencies: `pip install -e .`
- Check Python version (requires 3.10+)

### Documentation

- `ARCHITECTURE.md` - System design and architecture
- `IMPLEMENTATION_PROGRESS.md` - Current status and roadmap
- Tool docstrings - Individual tool documentation

---

🎯 **The foundation is solid - now let's build the user interfaces and complete the transformation!**