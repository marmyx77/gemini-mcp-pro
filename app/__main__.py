#!/usr/bin/env python3
"""
Gemini MCP Server - Legacy JSON-RPC Entry Point

DEPRECATED: This module is deprecated as of v3.0.0.
Use the FastMCP-based server instead:
    python run.py
    # or
    from app.server import main

This legacy handler is maintained only for backward compatibility.
It will be removed in v4.0.0.
"""

import sys
import json
import warnings
from typing import Dict, Any

# Issue deprecation warning
warnings.warn(
    "app.__main__ is deprecated since v3.0.0. "
    "Use 'python run.py' or 'from app.server import main' instead. "
    "This module will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2
)

from .core import config, structured_logger, log_activity
from .tools.registry import tool_registry


def send_response(response: Dict[str, Any]):
    """Send a JSON-RPC response to stdout."""
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def handle_initialize(request_id: Any) -> Dict[str, Any]:
    """Handle MCP initialize request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "gemini-mcp-pro",
                "version": config.version
            }
        }
    }


def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """Handle MCP tools/list request."""
    tools = tool_registry.get_tools_list()
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": tools
        }
    }


def handle_tool_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tools/call request."""
    import time
    import uuid

    tool_name = params.get("name", "")
    args = params.get("arguments", {})
    req_id = str(uuid.uuid4())[:8]

    # Check if tool is disabled
    if tool_name in config.disabled_tools:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": f"Tool '{tool_name}' is disabled"}],
                "isError": True
            }
        }

    # Check if tool exists
    if tool_name not in tool_registry:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Unknown tool: {tool_name}"
            }
        }

    start_time = time.time()
    log_activity(tool_name, "start", details={"args_keys": list(args.keys())}, request_id=req_id)

    try:
        result = tool_registry.call(tool_name, args)
        duration_ms = (time.time() - start_time) * 1000
        log_activity(tool_name, "success", duration_ms=duration_ms,
                    details={"result_len": len(result) if isinstance(result, str) else 0},
                    request_id=req_id)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": result}]
            }
        }
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        error_msg = str(e)
        log_activity(tool_name, "error", duration_ms=duration_ms, error=error_msg, request_id=req_id)

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": f"Error: {error_msg}"}],
                "isError": True
            }
        }


def main():
    """Main server loop - reads JSON-RPC requests from stdin, writes responses to stdout."""
    structured_logger.info(f"Gemini MCP Server v{config.version} starting")

    # SECURITY: Maximum request size to prevent DoS attacks
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB limit

    while True:
        try:
            # SECURITY: Limit input size to prevent memory exhaustion DoS
            line = sys.stdin.readline(MAX_REQUEST_SIZE)
            if not line:
                break

            # Check if input was truncated due to size limit
            if len(line) >= MAX_REQUEST_SIZE - 1:
                send_response({
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Request too large (max 10MB)"}
                })
                continue

            request = json.loads(line.strip())
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})

            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "notifications/initialized":
                continue  # No response needed
            elif method == "tools/list":
                response = handle_tools_list(request_id)
            elif method == "tools/call":
                response = handle_tool_call(request_id, params)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            send_response(response)

        except json.JSONDecodeError as e:
            # SECURITY: Return proper JSON-RPC 2.0 parse error (code -32700)
            send_response({
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
            })
            continue
        except EOFError:
            break
        except Exception as e:
            if 'request_id' in locals() and request_id:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                })


if __name__ == "__main__":
    main()
