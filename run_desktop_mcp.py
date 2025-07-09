#!/usr/bin/env python3
"""
Desktop MCP Launcher

Quick launcher for the Desktop MCP application.
Run this from the project root to start the full application.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path so we can import desktop_mcp
sys.path.insert(0, str(Path(__file__).parent / "src"))

from desktop_mcp.core.app import main

if __name__ == "__main__":
    asyncio.run(main())