# CLAUDE.md

This file provides context to Claude Code when working with this repository.

## Project Overview

This is an MCP (Model Context Protocol) server that bridges Claude Code with Google Gemini AI. It enables AI collaboration by allowing Claude to access Gemini's capabilities including text generation with thinking mode, web search, RAG, image generation, video generation, and text-to-speech.

**Version:** 1.0.0
**SDK:** google-genai (new GA SDK)

## Architecture

**Single-file MCP server** (`server.py`): A Python JSON-RPC server that:
- Communicates via stdin/stdout using MCP protocol
- Initializes the Gemini client with `google-genai` SDK
- Exposes 11 tools for various AI capabilities
- Uses unbuffered I/O for real-time communication

### Core Components

```
server.py
├── Model Mappings (MODELS, IMAGE_MODELS, VIDEO_MODELS, TTS_MODELS, TTS_VOICES)
├── JSON-RPC Handlers (initialize, tools/list, tools/call)
├── Tool Definitions (get_tools_list)
└── Tool Implementations (tool_* functions)
```

### Available Tools

| Tool | Function | Default Model |
|------|----------|---------------|
| `ask_gemini` | Text generation with thinking | Gemini 3 Pro |
| `gemini_code_review` | Code analysis | Gemini 3 Pro |
| `gemini_brainstorm` | Creative ideation | Gemini 3 Pro |
| `gemini_web_search` | Google-grounded search | Gemini 2.5 Flash |
| `gemini_file_search` | RAG document queries | Gemini 2.5 Flash |
| `gemini_create_file_store` | Create RAG stores | - |
| `gemini_upload_file` | Upload to RAG stores | - |
| `gemini_list_file_stores` | List RAG stores | - |
| `gemini_generate_image` | Image generation | Gemini 3 Pro Image |
| `gemini_generate_video` | Video generation | Veo 3.1 |
| `gemini_text_to_speech` | TTS with 30 voices | Gemini 2.5 Flash TTS |

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
