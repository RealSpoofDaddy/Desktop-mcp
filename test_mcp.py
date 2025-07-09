#!/usr/bin/env python3
"""
Test Desktop MCP Application

Quick test to verify the desktop MCP application works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import desktop_mcp
sys.path.insert(0, str(Path(__file__).parent / "src"))

from desktop_mcp.core.app import DesktopMCPApp

async def test():
    """Test the Desktop MCP application"""
    print("🧪 Testing Desktop MCP Application...")
    
    try:
        # Initialize the app
        app = DesktopMCPApp()
        print("✅ App instance created")
        
        # Initialize all subsystems
        results = await app.initialize()
        print(f"✅ Initialization complete: {results}")
        
        # Test command execution
        print("\n🔤 Testing command execution...")
        
        # Test opening calculator
        result = await app.execute_command("open calculator")
        print(f"📱 Calculator command: {result}")
        
        # Test taking screenshot
        result = await app.execute_command("take screenshot")
        print(f"📸 Screenshot command: {result}")
        
        # Get available tools
        tools = app.get_available_tools()
        print(f"🛠️ Available tools: {len(tools)}")
        
        # Get system status
        status = app.get_system_status()
        print(f"💻 System status: {status}")
        
        print("\n🎉 All tests passed! Desktop MCP is working correctly.")
        
        # Clean shutdown
        await app.shutdown()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())