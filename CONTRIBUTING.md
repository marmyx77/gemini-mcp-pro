# Contributing to Gemini MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive. We're all here to build something useful together.

## How to Contribute

### Reporting Issues

1. Check if the issue already exists
2. Use a clear, descriptive title
3. Include:
   - Python version
   - Claude Code version
   - Steps to reproduce
   - Expected vs actual behavior
   - Error messages (if any)

### Suggesting Features

Open an issue with:
- Clear description of the feature
- Use case / why it's needed
- Example of how it would work

### Pull Requests

1. **Fork and clone** the repository
2. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the code style below
4. **Test thoroughly**:
   ```bash
   # Test server starts
   GEMINI_API_KEY=your_key python3 server.py

   # Test tools work
   ./setup.sh YOUR_KEY
   # Then test in Claude Code
   ```
5. **Submit PR** with:
   - Clear description of changes
   - Link to related issue (if any)
   - Screenshots/examples for UI changes

## Code Style

### Python Guidelines

- **Python 3.8+** compatibility required
- **Type hints** for function parameters and returns
- **Docstrings** for public functions
- **Self-contained** tool implementations (minimize dependencies between tools)
- **User-friendly errors** - return helpful messages, not stack traces

### Example Tool Implementation

```python
def tool_example(param: str, optional: str = "default") -> str:
    """
    Brief description of what the tool does.

    Args:
        param: What this parameter does
        optional: What this optional parameter does

    Returns:
        Description of return value
    """
    try:
        # Implementation
        result = do_something(param)
        return f"Success: {result}"
    except Exception as e:
        return f"Error: {str(e)}"
```

### Adding a New Tool

See `CLAUDE.md` for the three-step process:
1. Add schema to `get_tools_list()`
2. Implement `tool_*` function
3. Register in `handle_tool_call()`

## Testing

### Manual Testing

```bash
# 1. Test server initialization
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | \
  GEMINI_API_KEY=your_key python3 server.py

# 2. Test tools/list
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | \
  GEMINI_API_KEY=your_key python3 server.py

# 3. Test a specific tool
echo '{"jsonrpc":"2.0","method":"tools/call","id":3,"params":{"name":"ask_gemini","arguments":{"prompt":"Hello"}}}' | \
  GEMINI_API_KEY=your_key python3 server.py
```

### Integration Testing

1. Install to Claude Code: `./setup.sh YOUR_KEY`
2. Restart Claude Code
3. Test each tool you modified
4. Verify no regressions in existing tools

## Commit Messages

Use clear, descriptive messages:

```
Add gemini_new_feature tool

- Implement feature X with parameters Y and Z
- Add error handling for edge case
- Update tool list and handler
```

## Documentation

Update documentation when you:
- Add a new tool
- Change existing tool behavior
- Add new configuration options
- Fix important bugs

Files to update:
- `README.md` - User-facing documentation
- `CLAUDE.md` - Developer context for AI assistants
- Tool docstrings in `server.py`

## Questions?

Open an issue with the "question" label if you need help or clarification.

---

Thank you for contributing!
