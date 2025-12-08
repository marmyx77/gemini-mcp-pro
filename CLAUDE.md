# CLAUDE.md

This file provides context to Claude Code when working with this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that bridges Claude Code with Google Gemini AI. It enables AI collaboration by allowing Claude to access Gemini's capabilities including text generation with thinking mode, web search, RAG, image analysis, image generation, video generation, and text-to-speech.

**Version:** 2.4.0
**SDK:** google-genai (new GA SDK)

## Architecture

**Single-file MCP server** (`server.py`): A Python JSON-RPC server that:
- Communicates via stdin/stdout using MCP protocol
- Initializes the Gemini client with `google-genai` SDK
- Exposes 15 tools for various AI capabilities
- Uses unbuffered I/O for real-time communication

### Core Components

```
server.py
├── Model Mappings (MODELS, IMAGE_MODELS, VIDEO_MODELS, TTS_MODELS, TTS_VOICES)
├── Conversation Memory System (ConversationTurn, ConversationThread, ConversationMemory)
├── JSON-RPC Handlers (initialize, tools/list, tools/call)
├── Tool Definitions (get_tools_list)
└── Tool Implementations (tool_* functions)
```

### Available Tools

| Tool | Function | Default Model |
|------|----------|---------------|
| `ask_gemini` | Text generation with thinking | Gemini 3 Pro |
| `gemini_code_review` | Code analysis | Gemini 3 Pro |
| `gemini_brainstorm` | Advanced brainstorming (6 methodologies) | Gemini 3 Pro |
| `gemini_web_search` | Google-grounded search | Gemini 2.5 Flash |
| `gemini_file_search` | RAG document queries | Gemini 2.5 Flash |
| `gemini_create_file_store` | Create RAG stores | - |
| `gemini_upload_file` | Upload to RAG stores | - |
| `gemini_list_file_stores` | List RAG stores | - |
| `gemini_analyze_image` | Image analysis (vision) | Gemini 2.5 Flash |
| `gemini_generate_image` | Image generation | Gemini 3 Pro Image |
| `gemini_generate_video` | Video generation | Veo 3.1 |
| `gemini_text_to_speech` | TTS with 30 voices | Gemini 2.5 Flash TTS |
| `gemini_analyze_codebase` | Large codebase analysis (1M context) | Gemini 3 Pro |
| `gemini_challenge` | Critical thinking / Devil's Advocate | Gemini 3 Pro |
| `gemini_generate_code` | Structured code generation | Gemini 3 Pro |

## Development Commands

### Run server locally for testing
```bash
GEMINI_API_KEY=your_key python3 server.py
```

### Test JSON-RPC manually
```bash
# Initialize
echo '{"jsonrpc":"2.0","method":"initialize","id":1}' | GEMINI_API_KEY=your_key python3 server.py

# List tools
echo '{"jsonrpc":"2.0","method":"tools/list","id":2}' | GEMINI_API_KEY=your_key python3 server.py
```

### Install to Claude Code
```bash
./setup.sh YOUR_API_KEY
```

### Reinstall after changes
```bash
cp server.py ~/.claude-mcp-servers/gemini-mcp-pro/
# Then restart Claude Code
```

## Code Style

- Python 3.8+ compatible
- Type hints for function signatures
- Docstrings for public functions
- Keep tool implementations self-contained
- Error handling returns user-friendly messages

## Adding a New Tool

1. **Add to `get_tools_list()`** - Define the tool schema:
```python
{
    "name": "gemini_new_tool",
    "description": "What the tool does",
    "inputSchema": {
        "type": "object",
        "properties": {
            "param": {"type": "string", "description": "Param description"}
        },
        "required": ["param"]
    }
}
```

2. **Implement the function** - Create `tool_new_tool()`:
```python
def tool_new_tool(param: str) -> str:
    """Implementation docstring"""
    # Implementation
    return "Result"
```

3. **Register in `handle_tool_call()`**:
```python
elif tool_name == "gemini_new_tool":
    result = tool_new_tool(args.get("param", ""))
```

## Key Configuration

- **API Key**: Via `GEMINI_API_KEY` environment variable (never hardcode)
- **Models**: Defined in `MODELS`, `IMAGE_MODELS`, `VIDEO_MODELS`, `TTS_MODELS` dicts
- **Install location**: `~/.claude-mcp-servers/gemini-mcp-pro/`

## Codebase Analysis (v2.1.0)

Large-scale code analysis using Gemini's 1M token context window.

### Tool: `gemini_analyze_codebase`
```python
def tool_analyze_codebase(
    prompt: str,                    # Analysis task
    files: List[str],               # File paths or glob patterns
    analysis_type: str = "general", # architecture|security|refactoring|documentation|dependencies|general
    model: str = "pro",
    continuation_id: str = None     # For iterative analysis
) -> str:
```

### Analysis Types
- `architecture`: Structure, design patterns, component relationships
- `security`: OWASP Top 10, input validation, auth patterns
- `refactoring`: DRY violations, code smells, design patterns
- `documentation`: Missing docs, unclear code, API completeness
- `dependencies`: Library usage, circular deps, package organization
- `general`: Comprehensive analysis

### Key Features
- Supports glob patterns: `['src/**/*.py', 'tests/*.py']`
- Auto-skips binary files and oversized files (>100KB)
- Conversation memory for iterative analysis
- Quota fallback to Flash model

## Security (v2.2.0)

Path sandboxing and file size validation to prevent attacks and resource exhaustion.

### Path Sandboxing
```python
def validate_path(file_path: str, allow_outside_sandbox: bool = False) -> str:
    """
    Security features:
    - Prevents directory traversal attacks (../)
    - Resolves symlinks to check actual destination
    - Blocks access outside SANDBOX_ROOT
    """
```

### File Size Pre-check
```python
def check_file_size(file_path: str, max_size: int = None) -> Optional[Dict]:
    """Rejects files BEFORE reading them into memory"""

def secure_read_file(file_path: str, max_size: int = None) -> str:
    """Combined path validation + size check + read"""
```

### Configuration
```bash
export GEMINI_SANDBOX_ROOT=/path/to/project  # Default: cwd
export GEMINI_SANDBOX_ENABLED=true           # Default: true
export GEMINI_MAX_FILE_SIZE=102400           # Default: 100KB
```

## Tool Management (v2.1.0)

### Disabling Tools
Reduce context bloat by disabling unused tools:
```bash
export GEMINI_DISABLED_TOOLS=gemini_generate_video,gemini_text_to_speech
```

### Prompt Size Limits
```python
MCP_PROMPT_SIZE_LIMIT = 60_000  # chars - prevents MCP transport errors
```

### Token Estimation
```python
def estimate_tokens(text: str) -> int:
    return len(text) // 4  # ~4 chars per token
```

## Conversation Memory (v2.0.0)

Multi-turn conversations with Gemini using `continuation_id` parameter.

### Core Components
```
server.py
├── ConversationTurn (dataclass) - Single turn with role, content, timestamp, files
├── ConversationThread (dataclass) - Thread with turns, TTL checking, context building
├── ConversationMemory (singleton) - Thread-safe storage with background cleanup
└── conversation_memory (global instance)
```

### Configuration
```python
CONVERSATION_TTL_HOURS = int(os.environ.get("GEMINI_CONVERSATION_TTL_HOURS", "3"))
CONVERSATION_MAX_TURNS = int(os.environ.get("GEMINI_CONVERSATION_MAX_TURNS", "50"))
```

### Usage Pattern
```python
# Tool receives continuation_id parameter
def tool_ask_gemini(prompt, ..., continuation_id=None):
    # Get or create thread
    thread_id, is_new, thread = conversation_memory.get_or_create_thread(continuation_id)

    # Build context from previous turns
    if not is_new:
        context = thread.build_context()
        full_prompt = f"{context}\n\n=== NEW REQUEST ===\n{prompt}"

    # Add user turn, call Gemini, add assistant turn
    conversation_memory.add_turn(thread_id, "user", prompt, "ask_gemini", files)
    # ... call Gemini ...
    conversation_memory.add_turn(thread_id, "assistant", response, "ask_gemini", [])

    # Return response with continuation_id
    return f"{response}\n\n---\n*continuation_id: {thread_id}*"
```

### Key Methods
- `conversation_memory.create_thread(metadata)` - Create new thread, returns UUID
- `conversation_memory.get_thread(thread_id)` - Get thread or None if expired
- `conversation_memory.add_turn(...)` - Add turn to thread
- `conversation_memory.get_or_create_thread(continuation_id)` - Returns (id, is_new, thread)
- `thread.build_context(max_tokens)` - Build formatted history for Gemini prompt
- `thread.is_expired()` - Check TTL
- `thread.can_add_turn()` - Check turn limit

## @File References (v1.3.0)

Tools that accept text input (`ask_gemini`, `gemini_brainstorm`, `gemini_code_review`) support @ syntax to include file contents:

- `@file.py` - Include single file contents
- `@src/main.py` - Path with directories
- `@*.py` - Glob patterns (max 10 files)
- `@src/**/*.ts` - Recursive glob patterns
- `@.` - Current directory listing
- `@src` - Directory listing

**Features:**
- Email addresses (user@example.com) are NOT expanded
- Large files truncated: 50KB for single files, 10KB per file for globs
- Files wrapped in markdown code blocks with filename header

**Example:**
```
ask_gemini("Review this code: @src/main.py")
gemini_code_review("@*.py", focus="security")
gemini_brainstorm("Improve @README.md documentation")
```

## Challenge Tool (v2.3.0)

Critical thinking tool that acts as a "Devil's Advocate" to find flaws in ideas/plans/code.

### Tool: `gemini_challenge`
```python
def tool_challenge(
    statement: str,       # The idea/plan/code to critique
    context: str = "",    # Optional background context
    focus: str = "general"  # general|security|performance|maintainability|scalability|cost
) -> str:
```

### Key Features
- Does NOT agree with the user - actively looks for problems
- Supports @file references for challenging code
- Structured output: Critical Flaws, Risks, Assumptions, Missing Considerations, Alternatives
- 6 focus areas for targeted critique

### Usage
```
gemini_challenge("We'll use microservices with 12 services",
                 context="3 developers, 2 month deadline",
                 focus="scalability")
```

## Activity Logging (v2.3.0)

Professional logging system for tool usage monitoring.

### Configuration
```bash
export GEMINI_ACTIVITY_LOG=true              # Enable/disable (default: true)
export GEMINI_LOG_DIR=~/.gemini-mcp-pro      # Log directory
export GEMINI_LOG_MAX_BYTES=10485760         # Max 10MB (default)
export GEMINI_LOG_BACKUP_COUNT=5             # Backup files (default: 5)
```

### Log Format
```
2025-12-08 14:30:00 | INFO | tool=ask_gemini | status=start | details={"args_keys": ["prompt", "model"]}
2025-12-08 14:30:05 | INFO | tool=ask_gemini | status=success | duration=5000ms | details={"result_len": 1234}
```

### Key Functions
```python
def log_activity(tool_name: str, status: str, duration_ms: float = 0,
                 details: Dict[str, Any] = None, error: str = None):
    """Log tool activity for usage monitoring - privacy-aware, truncates large values"""
```

## Code Generation Tool (v2.4.0)

Structured code generation for Claude to apply.

### Tool: `gemini_generate_code`
```python
def tool_generate_code(
    prompt: str,                    # What to generate
    context_files: List[str] = [],  # @file references for context
    language: str = "auto",         # auto|typescript|python|rust|go|java|...
    style: str = "production",      # production|prototype|minimal
    model: str = "pro"
) -> str:
```

### Output Format
```xml
<GENERATED_CODE>
<FILE action="create" path="src/components/Login.tsx">
// Complete file contents
</FILE>
<FILE action="modify" path="src/App.tsx">
// Modified file contents
</FILE>
</GENERATED_CODE>
```

### Style Modes
- `production`: Full error handling, types, docs, validation
- `prototype`: Working code with basic error handling
- `minimal`: Bare essentials only

### Usage
```
gemini_generate_code(
    prompt="Create a React login form with Tailwind CSS",
    context_files=["@src/App.tsx", "@package.json"],
    language="typescript",
    style="production"
)
```

## Gemini API Nuances

### Thinking Mode
- Gemini 3 Pro: Use `thinking_level` ("low" or "high")
- Gemini 2.5: Use `thinking_budget` (1024 for low, 8192 for high)
- Set `include_thoughts=True` to see reasoning process

### Web Search
- Uses `google_search` tool in config
- Grounding metadata contains source URLs
- Extract from `candidate.grounding_metadata.grounding_chunks`

### File Search (RAG)
- Stores persist on Google's servers
- Use `file_search_stores.create()` to make stores
- Upload with `file_search_stores.upload_to_file_search_store()`
- Query with `file_search` tool in generate_content config

### Image Analysis
- Uses `types.Part.from_bytes()` to send image data
- Supports PNG, JPG, JPEG, GIF, WEBP formats
- Default model: Gemini 2.5 Flash (reliable for vision)
- Gemini 3 Pro experimental for vision tasks

### Image Generation
- Pro model supports up to 4K resolution
- Flash model limited to 1024px
- Response contains `inline_data` with image bytes

### Video Generation
- Veo 3.1 supports native audio (dialogue, effects, ambient)
- 1080p requires 8 second duration
- Use polling with `operations.get()` for completion
- Can take 1-6 minutes to generate

### Text-to-Speech
- 30 voice options with different characteristics
- Multi-speaker supports up to 2 voices
- Output is PCM 24kHz, 16-bit, mono WAV

## Security Notes

- Never commit API keys
- API key should be passed via environment variable
- Test files (test_*.png, test_*.mp4) are git-ignored
- The server validates API key presence before initializing client
