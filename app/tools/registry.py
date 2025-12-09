"""
Tool Registry with FastAPI-style decorator registration.

Usage:
    from app.tools.registry import tool_registry, tool

    @tool(
        name="my_tool",
        description="Does something useful",
        input_schema={...}  # Optional: auto-generated from type hints
    )
    def my_tool(param: str, count: int = 10) -> str:
        '''Tool docstring becomes description if not provided.'''
        return f"Result: {param}"

    # Or with Pydantic model:
    @tool(name="my_tool", input_model=MyInputModel)
    def my_tool(params: MyInputModel) -> str:
        return f"Result: {params.value}"
"""

import sys
import inspect
import importlib
import importlib.util
from pathlib import Path
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, Union
from dataclasses import dataclass, field

try:
    from pydantic import BaseModel, create_model
    from pydantic.fields import FieldInfo
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = None


@dataclass
class ToolDefinition:
    """Definition of a registered tool."""
    name: str
    description: str
    handler: Callable
    input_schema: Dict[str, Any]
    input_model: Optional[Type] = None  # Pydantic model if available
    tags: List[str] = field(default_factory=list)


class ToolRegistry:
    """
    Central registry for MCP tools with decorator-based registration.

    Features:
    - @tool decorator for simple registration
    - Auto-generates JSON schema from type hints
    - Supports Pydantic models for validation
    - Plugin discovery from directory
    - Entry point discovery for pip-installed plugins
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._disabled: List[str] = []

    def register(
        self,
        name: str,
        handler: Callable,
        description: str = None,
        input_schema: Dict[str, Any] = None,
        input_model: Type = None,
        tags: List[str] = None
    ) -> None:
        """
        Register a tool directly.

        Args:
            name: Unique tool name
            handler: Callable that implements the tool
            description: Tool description (uses docstring if not provided)
            input_schema: MCP-compatible JSON schema for inputs
            input_model: Pydantic model for validation
            tags: Optional tags for categorization
        """
        if name in self._disabled:
            return

        # Use docstring if no description
        if description is None:
            description = handler.__doc__ or f"Tool: {name}"
        description = description.strip().split('\n')[0]  # First line only

        # Generate schema if not provided
        if input_schema is None:
            input_schema = self._generate_schema(handler, input_model)

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            handler=handler,
            input_schema=input_schema,
            input_model=input_model,
            tags=tags or []
        )

    def _generate_schema(self, handler: Callable, input_model: Type = None) -> Dict[str, Any]:
        """Generate JSON schema from function signature or Pydantic model."""

        # Use Pydantic model schema if available
        if input_model is not None and PYDANTIC_AVAILABLE:
            schema = input_model.model_json_schema()
            return {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", [])
            }

        # Generate from function signature
        sig = inspect.signature(handler)
        properties = {}
        required = []

        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean",
            list: "array",
            dict: "object",
        }

        for param_name, param in sig.parameters.items():
            if param_name in ('self', 'cls'):
                continue

            # Get type hint
            if param.annotation != inspect.Parameter.empty:
                py_type = param.annotation
                # Handle Optional types
                if hasattr(py_type, '__origin__'):
                    if py_type.__origin__ is Union:
                        args = [a for a in py_type.__args__ if a is not type(None)]
                        py_type = args[0] if args else str
                json_type = type_map.get(py_type, "string")
            else:
                json_type = "string"

            prop = {"type": json_type}

            # Add description from docstring if available (TODO: parse docstring)
            properties[param_name] = prop

            # Check if required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                prop["default"] = param.default

        return {
            "type": "object",
            "properties": properties,
            "required": required
        }

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self._tools.get(name)

    def execute(self, name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with given arguments.

        Args:
            name: Tool name
            args: Arguments to pass to the tool

        Returns:
            Tool result

        Raises:
            KeyError: If tool not found
            ValueError: If validation fails
        """
        tool_def = self._tools.get(name)
        if not tool_def:
            raise KeyError(f"Unknown tool: {name}")

        # Validate with Pydantic model if available
        if tool_def.input_model is not None and PYDANTIC_AVAILABLE:
            validated = tool_def.input_model(**args)
            args = validated.model_dump()

        return tool_def.handler(**args)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Get MCP-compatible tool definitions list."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            }
            for tool in self._tools.values()
        ]

    # Alias for backwards compatibility
    def get_tools_list(self) -> List[Dict[str, Any]]:
        """Alias for list_tools() for backwards compatibility."""
        return self.list_tools()

    def call(self, name: str, args: Dict[str, Any]) -> Any:
        """Alias for execute() for compatibility with __main__.py."""
        return self.execute(name, args)

    def disable(self, names: List[str]) -> None:
        """Disable tools by name."""
        self._disabled.extend(names)
        for name in names:
            self._tools.pop(name, None)

    def discover_plugins(self, plugins_dir: Path) -> int:
        """
        Discover and load plugins from a directory.

        Each plugin file should either:
        1. Use @tool decorator to register tools
        2. Export a `register(registry)` function

        SECURITY: Validates directory permissions before loading any plugins.
        Rejects world-writable directories to prevent code injection attacks.

        Args:
            plugins_dir: Path to plugins directory

        Returns:
            Number of plugins loaded

        Raises:
            PermissionError: If directory has insecure permissions
        """
        if not plugins_dir.exists():
            return 0

        # SECURITY: Check directory permissions to prevent code injection
        # Reject world-writable directories
        try:
            stat_info = plugins_dir.stat()
            if stat_info.st_mode & 0o002:  # World-writable
                raise PermissionError(
                    f"Plugin directory '{plugins_dir}' is world-writable. "
                    "This is a security risk. Please run: chmod o-w {plugins_dir}"
                )
            # Also check if group-writable (optional, but good practice)
            if stat_info.st_mode & 0o020:
                print(f"[plugin] Warning: '{plugins_dir}' is group-writable", file=sys.stderr)
        except OSError as e:
            raise PermissionError(f"Cannot check permissions for '{plugins_dir}': {e}")

        loaded = 0
        for plugin_file in plugins_dir.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue

            try:
                spec = importlib.util.spec_from_file_location(
                    plugin_file.stem, plugin_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Check for register function
                if hasattr(module, 'register'):
                    module.register(self)

                loaded += 1
                print(f"[plugin] Loaded: {plugin_file.name}", file=sys.stderr)

            except Exception as e:
                print(f"[plugin] Failed to load {plugin_file.name}: {e}", file=sys.stderr)

        return loaded

    def discover_entrypoints(self, group: str = "gemini_mcp.plugins") -> int:
        """
        Discover plugins from installed packages via entry points.

        Packages register via pyproject.toml:
        [project.entry-points."gemini_mcp.plugins"]
        my_tool = "my_package:MyTool"

        Returns:
            Number of plugins loaded
        """
        try:
            import importlib.metadata
            eps = importlib.metadata.entry_points(group=group)
            loaded = 0

            for ep in eps:
                try:
                    plugin = ep.load()
                    if callable(plugin):
                        plugin(self)
                    loaded += 1
                    print(f"[entrypoint] Loaded: {ep.name}", file=sys.stderr)
                except Exception as e:
                    print(f"[entrypoint] Failed to load {ep.name}: {e}", file=sys.stderr)

            return loaded
        except Exception:
            return 0

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# Global registry instance
tool_registry = ToolRegistry()


def tool(
    name: str = None,
    description: str = None,
    input_schema: Dict[str, Any] = None,
    input_model: Type = None,
    tags: List[str] = None
) -> Callable:
    """
    Decorator to register a function as an MCP tool.

    Usage:
        @tool(name="greet", description="Greet someone")
        def greet(name: str, greeting: str = "Hello") -> str:
            return f"{greeting}, {name}!"

        # Or with auto-detection:
        @tool()
        def greet(name: str) -> str:
            '''Greet someone by name.'''
            return f"Hello, {name}!"
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__

        tool_registry.register(
            name=tool_name,
            handler=func,
            description=description,
            input_schema=input_schema,
            input_model=input_model,
            tags=tags
        )

        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper._tool_name = tool_name
        wrapper._is_mcp_tool = True

        return wrapper

    return decorator
