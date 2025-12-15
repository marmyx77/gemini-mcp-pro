"""
gemini-mcp-pro v3.3.0
Production MCP server for Google Gemini AI.

Features:
- FastMCP SDK for protocol compliance
- 18 tools including Deep Research and Conversation Management
- Dual conversation storage: local (SQLite) or cloud (Interactions API)
- Security: sandboxing, secrets sanitization, cross-platform file locking
"""

__version__ = "3.3.0"

from .server import main

__all__ = ["__version__", "main"]
