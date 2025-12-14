"""
gemini-mcp-pro v3.1.0
Production MCP server for Google Gemini AI.

Features:
- FastMCP SDK for protocol compliance
- 15 tools focused on Gemini strengths
- SQLite persistence for conversation history
- Security: sandboxing, secrets sanitization, atomic writes
"""

__version__ = "3.1.0"

from .server import main

__all__ = ["__version__", "main"]
