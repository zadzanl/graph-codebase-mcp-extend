#!/usr/bin/env python3
"""
Standalone MCP Server Launcher for Graph-Codebase-MCP

This script starts the MCP server to provide AI agents access to the codebase knowledge graph.
The knowledge graph must be pre-populated by running src/main.py first.
"""

import os
import sys
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.abspath(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Load environment variables
load_dotenv()

# Import and run the MCP server
from src.mcp.server import main

if __name__ == "__main__":
    main()
