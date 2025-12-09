"""
gemini-mcp-pro v3.0.2
Production MCP server for Google Gemini AI.

Features:
- FastMCP SDK for protocol compliance
- 15 tools focused on Gemini strengths
- SQLite persistence for conversation history
- Security: sandboxing, secrets sanitization, atomic writes
"""

__version__ = "3.0.2"

# Import from FastMCP server (v3.0.0)
# Falls back to legacy JSON-RPC if mcp not installed
try:
    from .server import main
except ImportError:
    # Fallback to legacy manual JSON-RPC implementation
    from .__main__ import main

__all__ = ["__version__", "main"]
