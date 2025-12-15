# gemini-mcp-pro

A full-featured MCP server for Google Gemini. Access advanced reasoning, web search, RAG, image analysis, image generation, video creation, and text-to-speech from any MCP-compatible client (Claude Desktop, Claude Code, Cursor, and more).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![Version 3.3.0](https://img.shields.io/badge/version-3.3.0-green.svg)](https://github.com/marmyx/gemini-mcp-pro/releases)

## 🚀 What's New in v3.3.0

**Interactions API Integration & Dual Storage Mode** - Your conversations, your way!

```python
# Local mode (default) - Fast SQLite storage
ask_gemini("Analyze this code", mode="local")

# Cloud mode - 55-day retention on Google servers
ask_gemini("Review my architecture", mode="cloud", title="Architecture Review")
# Returns: continuation_id: int_v1_abc123...

# Resume from ANY device
ask_gemini("What about security?", continuation_id="int_v1_abc123...")
```

### 🌐 Interactions API (v3.2.0 + v3.3.0)

| Tool | API Mode | Use Case |
|------|----------|----------|
| `gemini_deep_research` | Background (5-60 min) | Autonomous multi-step research with comprehensive reports |
| `ask_gemini` with `mode="cloud"` | Synchronous | Cloud-persisted conversations with 55-day retention |

### ✨ v3.3.0 Features

- ☁️ **Dual Storage**: `mode="local"` (SQLite) or `mode="cloud"` (Interactions API)
- 📋 **Conversation Management**: `gemini_list_conversations`, `gemini_delete_conversation`
- 📝 **Named Conversations**: `title="My Project"` for easy retrieval
- 🔧 **Configurable Models**: Override via `GEMINI_MODEL_PRO`, `GEMINI_MODEL_FLASH`, etc.
- 🖥️ **Cross-Platform**: File locking works on Windows, macOS, and Linux

> Now 18 tools total with conversation management!

---

## Why This Exists

Claude is exceptional at reasoning and code generation, but sometimes you want:
- A **second opinion** from a different AI perspective
- **Multi-turn conversations** with context memory
- Access to **real-time web search** with Google grounding
- **Autonomous deep research** that runs for minutes and produces comprehensive reports
- **Image analysis** with vision capabilities (OCR, description, Q&A)
- **Native image generation** with Gemini's models (up to 4K)
- **Video generation** with Veo 3.1 (state-of-the-art, includes audio)
- **Text-to-speech** with 30 natural voices
- **RAG capabilities** for querying your documents
- **Deep thinking mode** for complex reasoning tasks
- **Large codebase analysis** with 1M token context window

This MCP server bridges Claude Code with Google Gemini, enabling seamless AI collaboration.

## Features

### Text & Reasoning
| Tool | Description | Default Model |
|------|-------------|---------------|
| `ask_gemini` | Ask questions with optional thinking mode and conversation modes | Gemini 3 Pro |
| `gemini_code_review` | Security, performance, and code quality analysis | Gemini 3 Pro |
| `gemini_brainstorm` | Creative ideation with 6 methodologies | Gemini 3 Pro |
| `gemini_analyze_codebase` | Large-scale codebase analysis (1M context) | Gemini 3 Pro |
| `gemini_challenge` | Critical thinking - find flaws in ideas/plans/code | Gemini 3 Pro |
| `gemini_generate_code` | Structured code generation for Claude to apply | Gemini 3 Pro |

### Conversation Management (NEW in v3.3.0)
| Tool | Description |
|------|-------------|
| `gemini_list_conversations` | List all conversations with title, mode, last activity, turn count |
| `gemini_delete_conversation` | Delete conversations by ID or title (partial match supported) |

### Web & Knowledge
| Tool | Description | Default Model |
|------|-------------|---------------|
| `gemini_web_search` | Real-time search with Google grounding & citations | Gemini 2.5 Flash |
| `gemini_deep_research` | **NEW** Autonomous multi-step research (5-60 min) | Deep Research Agent |
| `gemini_file_search` | RAG queries on uploaded documents | Gemini 2.5 Flash |
| `gemini_create_file_store` | Create document stores for RAG | - |
| `gemini_upload_file` | Upload files to stores (PDF, DOCX, code, etc.) | - |
| `gemini_list_file_stores` | List available document stores | - |

### Multi-Modal
| Tool | Description | Models |
|------|-------------|--------|
| `gemini_analyze_image` | Analyze images (describe, OCR, Q&A) | Gemini 2.5 Flash, 3 Pro |
| `gemini_generate_image` | Native image generation (up to 4K) | Gemini 3 Pro, 2.5 Flash |
| `gemini_generate_video` | Video with audio (4-8 sec, 720p/1080p) | Veo 3.1, Veo 3, Veo 2 |
| `gemini_text_to_speech` | Natural TTS with 30 voices | Gemini 2.5 Flash/Pro TTS |

## Quick Start

### Prerequisites

- Python 3.9+
- Claude Code CLI ([installation guide](https://claude.ai/code))
- Google Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Installation

**Option 1: Automatic Setup (Recommended)**

```bash
git clone https://github.com/marmyx/gemini-mcp-pro.git
cd gemini-mcp-pro
./setup.sh YOUR_GEMINI_API_KEY
```

**Option 2: Manual Setup**

1. Install dependencies:
```bash
pip install google-genai pydantic
```

2. Create the MCP server directory:
```bash
mkdir -p ~/.claude-mcp-servers/gemini-mcp-pro
cp -r app/ ~/.claude-mcp-servers/gemini-mcp-pro/
cp run.py ~/.claude-mcp-servers/gemini-mcp-pro/
```

3. Register with Claude Code:
```bash
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=YOUR_API_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/run.py
```

4. Restart Claude Code to activate.

### Verify Installation

```bash
claude mcp list
# Should show: gemini-mcp-pro: Connected
```

## Architecture (v3.3.0)

The server uses a **modular architecture** with FastMCP SDK for maintainability and extensibility:

```
gemini-mcp-pro/
├── run.py                    # Entry point
├── pyproject.toml            # Package configuration
├── app/
│   ├── __init__.py          # Package init, exports main(), __version__
│   ├── server.py            # FastMCP server (18 @mcp.tool() registrations)
│   ├── core/                # Infrastructure
│   │   ├── config.py        # Environment configuration, version, model IDs
│   │   ├── logging.py       # Structured JSON logging
│   │   └── security.py      # Sandboxing, sanitization, cross-platform file locking
│   ├── services/            # External integrations
│   │   ├── gemini.py        # Gemini API client with fallback
│   │   └── persistence.py   # SQLite conversation storage with conversation index
│   ├── tools/               # MCP tool implementations (by domain)
│   │   ├── text/            # ask_gemini, code_review, brainstorm, challenge, conversations
│   │   ├── code/            # analyze_codebase (5MB limit), generate_code (dry-run)
│   │   ├── media/           # image/video generation, TTS, vision
│   │   ├── web/             # web_search, deep_research
│   │   └── rag/             # file_store, file_search, upload
│   ├── utils/               # Helpers
│   │   ├── file_refs.py     # @file expansion with line numbers
│   │   └── tokens.py        # Token estimation
│   └── schemas/             # Pydantic v2 validation
│       └── inputs.py        # Tool input schemas
└── tests/                   # Test suite (118+ tests)
```


## Usage Examples

### Basic Questions

Ask Gemini for a second opinion or different perspective:

```
"Ask Gemini to explain the trade-offs between microservices and monolithic architectures"
```

### Code Review

Get thorough code analysis with security focus:

```
"Have Gemini review this authentication function for security issues"
```

### @File References

Include file contents directly in prompts using @ syntax:

```
# Review a specific file
"Ask Gemini to review @src/auth.py for security issues"

# Review multiple files with glob patterns
"Gemini code review @*.py with focus on performance"

# Brainstorm improvements for a project
"Brainstorm improvements for @README.md documentation"
```

**Supported patterns:**
- `@file.py` - Single file
- `@src/main.py` - Path with directories
- `@*.py` - Glob patterns (max 10 files)
- `@src/**/*.ts` - Recursive glob
- `@.` - Current directory listing

### Conversation Memory

Gemini can remember previous context across multiple calls using `continuation_id`:

```
# First call - Gemini analyzes the code
"Ask Gemini to analyze @src/auth.py for security issues"
# Response includes: continuation_id: abc-123-def

# Follow-up call - Gemini remembers the previous analysis!
"Ask Gemini (continuation_id: abc-123-def) how to fix the SQL injection"
# Gemini knows exactly which file and issue you're referring to
```

### 🌐 Dual Storage Mode (v3.3.0)

Choose where your conversations are stored:

| Mode | Storage | Retention | Best For |
|------|---------|-----------|----------|
| `local` (default) | SQLite | 3 hours (configurable) | Quick chats, development |
| `cloud` | Google Interactions API | 55 days | Long-term projects, cross-device |

```
# Start a cloud conversation with a title
"Ask Gemini (mode=cloud, title='Architecture Review'): Review my microservices design"
# Returns: continuation_id: int_v1_abc123...

# Resume from any device, any time (within 55 days)
"Ask Gemini (continuation_id: int_v1_abc123...): What about the database layer?"

# List all your conversations
"List my Gemini conversations"
# Shows: | Architecture Review | ☁️ cloud | 2 turns | 5m ago |
```

### 🔬 Deep Research (v3.2.0)

Autonomous multi-step research that runs 5-60 minutes:

```
"Deep research: Compare React, Vue, and Svelte for enterprise applications in 2025"
```

The Deep Research Agent will:
1. **Plan** a comprehensive research strategy
2. **Execute** multiple targeted web searches
3. **Synthesize** findings from dozens of sources
4. **Produce** a detailed report with citations

Use cases:
- Market research and competitive analysis
- Technical deep dives and literature reviews
- Trend analysis and industry reports
- Any topic requiring thorough investigation

### Codebase Analysis

Leverage Gemini's 1M token context to analyze entire codebases at once:

```
# Analyze project architecture
"Analyze codebase src/**/*.py with focus on architecture"

# Security audit of entire project
"Analyze codebase ['src/', 'lib/'] for security vulnerabilities"

# Iterative analysis with memory
"Analyze codebase src/ - what refactoring opportunities exist?"
# Then follow up with continuation_id for deeper analysis
```

**Analysis types:** `architecture`, `security`, `refactoring`, `documentation`, `dependencies`, `general`

### Web Search

Access real-time information with citations:

```
"Search the web with Gemini for the latest React 19 features"
```

### Image Analysis

Analyze existing images - describe, extract text, or ask questions:

```
"Analyze this image and describe what you see: /path/to/image.png"
```

For OCR (text extraction):
```
"Extract all text from this screenshot: /path/to/screenshot.png"
```

**Supported formats:** PNG, JPG, JPEG, GIF, WEBP

### Image Generation

Generate high-quality images:

```
"Generate an image of a futuristic Tokyo street at night, neon lights reflecting on wet pavement,
cinematic composition, shot on 35mm lens"
```

**Pro tips for image generation:**
- Use descriptive sentences, not keyword lists
- Specify style, lighting, camera angle, mood
- For photorealism: mention lens type, lighting setup
- For illustrations: specify art style, colors, line style

### Video Generation

Create short videos with native audio:

```
"Generate a video of ocean waves crashing on rocky cliffs at sunset,
seagulls flying overhead, sound of waves and wind"
```

**Video capabilities:**
- Duration: 4-8 seconds
- Resolution: 720p or 1080p (1080p requires 8s duration)
- Native audio: dialogue, sound effects, ambient sounds
- For dialogue: use quotes ("Hello," she said)
- For sounds: describe explicitly (engine roaring, birds chirping)
- Async polling: Non-blocking generation (v3.0.1+)

### Text-to-Speech

Convert text to natural speech:

```
"Convert this text to speech using the Aoede voice:
Welcome to our product demonstration. Today we'll explore..."
```

**Available voice styles:**
- Bright: Zephyr, Autonoe
- Upbeat: Puck, Laomedeia
- Informative: Charon, Rasalgethi
- Warm: Sulafat, Vindemiatrix
- Firm: Kore
- And 21 more...

**Multi-speaker dialogue:**
```
speakers: [
  {"name": "Host", "voice": "Charon"},
  {"name": "Guest", "voice": "Aoede"}
]
text: "Host: Welcome to the show!\nGuest: Thanks for having me!"
```

### RAG (Document Search)

Query your documents with citations:

```
# 1. Create a store
"Create a Gemini file store called 'project-docs'"

# 2. Upload files
"Upload the technical specification PDF to the project-docs store"

# 3. Query
"Search the project-docs store: What are the API rate limits?"
```

### Challenge Tool

Get critical analysis before implementing - find flaws early:

```
"Challenge this plan with focus on security: We'll store user passwords in a JSON file
and use a simple hash for authentication"
```

Focus areas: `general`, `security`, `performance`, `maintainability`, `scalability`, `cost`

The tool acts as a "Devil's Advocate" - it will NOT agree with you. It actively looks for:
- Critical flaws that must be fixed
- Significant risks
- Questionable assumptions
- Missing considerations
- Better alternatives

### Code Generation

Let Gemini generate code that Claude can apply:

```
"Generate a Python FastAPI endpoint for user authentication with JWT tokens"
```

The output uses structured XML format:
```xml
<GENERATED_CODE>
<FILE action="create" path="src/auth.py">
# Complete code here...
</FILE>
</GENERATED_CODE>
```

Options:
- **language**: auto, typescript, python, rust, go, java, etc.
- **style**: production (full), prototype (basic), minimal (bare)
- **context_files**: Include existing files for style matching
- **output_dir**: Auto-save generated files to directory
- **dry_run**: Preview files without writing (v3.0.1+)

### Thinking Mode

Enable deep reasoning for complex problems:

```
"Ask Gemini with high thinking level:
Design an optimal database schema for a social media platform with
posts, comments, likes, and follows. Consider scalability."
```

Thinking levels:
- `off`: Standard response (default)
- `low`: Quick reasoning (faster)
- `high`: Deep analysis (more thorough)

## Model Selection

### Text Models

| Alias | Model | Best For |
|-------|-------|----------|
| `pro` | Gemini 3 Pro | Complex reasoning, coding, analysis (default) |
| `flash` | Gemini 2.5 Flash | Balanced speed/quality |
| `fast` | Gemini 2.5 Flash | High-volume, simple tasks |

### Image Models

| Alias | Model | Capabilities |
|-------|-------|--------------|
| `pro` | Gemini 3 Pro Image | 4K resolution, thinking mode, highest quality |
| `flash` | Gemini 2.5 Flash Image | Fast generation, 1024px max |

### Video Models

| Alias | Model | Capabilities |
|-------|-------|--------------|
| `veo31` | Veo 3.1 | Best quality, 720p/1080p, native audio |
| `veo31_fast` | Veo 3.1 Fast | Optimized for speed |
| `veo3` | Veo 3.0 | Stable, with audio |
| `veo3_fast` | Veo 3.0 Fast | Fast stable version |
| `veo2` | Veo 2.0 | Legacy, no audio |

## Configuration

### Environment Variables

```bash
# Required
export GEMINI_API_KEY="your-api-key-here"

# Optional: Conversation Memory
export GEMINI_CONVERSATION_TTL_HOURS=3    # Thread expiration (default: 3)
export GEMINI_CONVERSATION_MAX_TURNS=50   # Max turns per thread (default: 50)

# Optional: Tool Management
export GEMINI_DISABLED_TOOLS=gemini_generate_video,gemini_text_to_speech  # Reduce context bloat

# Optional: Security
export GEMINI_SANDBOX_ROOT=/path/to/project  # Restrict file access to this directory
export GEMINI_SANDBOX_ENABLED=true           # Enable/disable sandboxing (default: true)
export GEMINI_MAX_FILE_SIZE=102400           # Max file size in bytes (default: 100KB)

# Optional: Activity Logging
export GEMINI_ACTIVITY_LOG=true              # Enable/disable activity logging (default: true)
export GEMINI_LOG_DIR=~/.gemini-mcp-pro      # Log directory (default: ~/.gemini-mcp-pro)
export GEMINI_LOG_FORMAT=json                # Log format: "json" or "text" (default: text)
```

### Server Location

The server is installed at: `~/.claude-mcp-servers/gemini-mcp-pro/`

### Update API Key

```bash
# Option 1: Environment variable (recommended)
claude mcp remove gemini-mcp-pro
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=NEW_API_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/run.py

# Option 2: Re-run setup
./setup.sh NEW_API_KEY
```

## Docker Deployment

Production-ready Docker container with security hardening:

```bash
# Build and run
docker-compose up -d

# With monitoring (log viewer at port 8080)
docker-compose --profile monitoring up -d
```

### Docker Features
- Non-root user execution
- Health check every 30 seconds
- Read-only filesystem with tmpfs
- Resource limits (2 CPU, 2GB RAM)
- Log rotation (10MB max, 3 files)

## Troubleshooting

### MCP not showing up

```bash
# Check registration
claude mcp list

# Re-register
claude mcp remove gemini-mcp-pro
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=YOUR_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/run.py

# Restart Claude Code
```

### Connection errors

1. Verify your API key is valid at [AI Studio](https://aistudio.google.com/)
2. Check Python has the SDK: `pip show google-genai`
3. Test manually:
```bash
GEMINI_API_KEY=your_key python3 ~/.claude-mcp-servers/gemini-mcp-pro/run.py
# Send: {"jsonrpc":"2.0","method":"initialize","id":1}
```

### Video/Image generation timeouts

- Video generation can take 1-6 minutes
- Large images (4K) may take longer
- The server has a 6-minute timeout for video generation

## API Costs

| Feature | Approximate Cost |
|---------|-----------------|
| Text generation | Free tier available / $0.075-0.30 per 1M tokens |
| Web Search | ~$14 per 1000 queries |
| File Search indexing | $0.15 per 1M tokens (one-time) |
| File Search storage | Free |
| Image generation | Varies by resolution |
| Video generation | Varies by duration/resolution |
| Text-to-speech | Varies by length |

See [Google AI pricing](https://ai.google.dev/pricing) for current rates.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policies and how to report vulnerabilities.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Previous Releases

### v3.2.0 - Deep Research Agent
- `gemini_deep_research`: Autonomous multi-step research (5-60 min)
- First integration with Google's Interactions API
- Comprehensive reports with citations

### v3.1.0 - Technical Debt Cleanup
- Removed 604 lines of deprecated code
- RAG short name resolution for stores

### v3.0.0 - FastMCP Migration
- Migrated to official MCP Python SDK (FastMCP)
- SQLite persistence for conversations
- Comprehensive security hardening

See [CHANGELOG.md](CHANGELOG.md) for full release notes.

## Roadmap

| Release | Focus | Status |
|---------|-------|--------|
| **v3.3.0** | Interactions API + Dual Mode | ✅ Released - Cloud mode for ask_gemini, conversation management |
| **v3.2.0** | Deep Research Agent | ✅ Released - `gemini_deep_research` using Interactions API |
| **v4.0.0** | Full Cloud Migration | 🔮 Planned - All tools use Interactions API, local vector store |

---

Built for the Claude Code community | [SECURITY.md](SECURITY.md) | [CONTRIBUTING.md](CONTRIBUTING.md)
