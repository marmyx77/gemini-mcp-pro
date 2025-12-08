# Contributing to Gemini MCP Server

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful and constructive. We're all here to build something useful together.

## Roadmap & Feature Requests

### Current Version: 2.5.0

### Recently Completed
- **v2.5.0** - Dynamic Line Numbering, Code Gen Auto-Save, JSON More Info Protocol
- **v2.4.0** - Code Generation Tool (`gemini_generate_code`)
- **v2.3.0** - ChallengeTool + Activity Logging
- **v2.2.0** - Security (Path Sandboxing, File Size Limits)
- **v2.1.0** - Codebase Analysis (1M context)
- **v2.0.0** - Conversation Memory

### Planned Features (Contributions Welcome!)

| Version | Feature | Priority | Complexity | Description |
|---------|---------|----------|------------|-------------|
| v3.0.0 | **BaseTool Refactor** | Low | Medium | Class-based tools with Pydantic schemas |
| v3.0.0 | **Model Capabilities** | Low | Medium | Structured model info (context window, features) |
| v3.0.0 | **Async Video** | Medium | Medium | Non-blocking video generation with job polling |

### Easy First Contributions

1. **Test Coverage** - Add unit tests for security functions
2. **Documentation** - Improve examples and use cases
3. **Voice Samples** - Document TTS voice characteristics

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

### Security Guidelines (v2.2.0+)

All file operations MUST use the security functions:

```python
# Always validate paths before file operations
from server import validate_path, check_file_size, secure_read_file

# Option 1: Use secure_read_file (recommended)
content = secure_read_file(file_path)

# Option 2: Manual validation
safe_path = validate_path(file_path)  # Raises PermissionError if outside sandbox
size_error = check_file_size(safe_path)  # Returns error dict if too large
if size_error:
    return f"Error: {size_error['message']}"
```

**Security checklist for new tools:**
- [ ] Use `validate_path()` for any file path input
- [ ] Use `check_file_size()` before reading files
- [ ] Never expose raw exception details to users
- [ ] Respect `SANDBOX_ROOT` boundaries

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

### Security Testing (Required for v2.2.0+)

```python
# Run security tests before submitting PRs
python3 -c "
import server

# Test 1: Path within sandbox should work
try:
    path = server.validate_path('server.py')
    print(f'✅ Sandbox OK: {path}')
except Exception as e:
    print(f'❌ Sandbox failed: {e}')

# Test 2: Path outside sandbox should be blocked
try:
    server.validate_path('/etc/passwd')
    print('❌ Security FAIL: /etc/passwd not blocked!')
except PermissionError:
    print('✅ Security OK: /etc/passwd blocked')

# Test 3: Directory traversal should be blocked
try:
    server.validate_path('../../../etc/passwd')
    print('❌ Security FAIL: traversal not blocked!')
except PermissionError:
    print('✅ Security OK: traversal blocked')

# Test 4: File size check
result = server.check_file_size('server.py', max_size=1000)
if result:
    print('✅ Size check OK: large file rejected')
else:
    print('✅ Size check OK: small file accepted')
"
```

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
- `CHANGELOG.md` - Version history (follow Keep a Changelog format)
- `SECURITY.md` - Security policies and features
- Tool docstrings in `server.py`

### Architecture Reference

See `.comparison/COMPARISON.md` for:
- Competitive analysis vs other MCP servers
- Feature roadmap and rationale

## Questions?

Open an issue with the "question" label if you need help or clarification.

---

Thank you for contributing!
