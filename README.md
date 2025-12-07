# gemini-mcp-pro

A full-featured MCP server for Google Gemini. Access advanced reasoning, web search, RAG, image generation, video creation, and text-to-speech from any MCP-compatible client (Claude Desktop, Claude Code, Cursor, and more).

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

## Why This Exists

Claude is exceptional at reasoning and code generation, but sometimes you want:
- A **second opinion** from a different AI perspective
- Access to **real-time web search** with Google grounding
- **Native image generation** with Gemini's models (up to 4K)
- **Video generation** with Veo 3.1 (state-of-the-art, includes audio)
- **Text-to-speech** with 30 natural voices
- **RAG capabilities** for querying your documents
- **Deep thinking mode** for complex reasoning tasks

This MCP server bridges Claude Code with Google Gemini, enabling seamless AI collaboration.

## Features

### Text & Reasoning
| Tool | Description | Default Model |
|------|-------------|---------------|
| `ask_gemini` | Ask questions with optional thinking mode | Gemini 3 Pro |
| `gemini_code_review` | Security, performance, and code quality analysis | Gemini 3 Pro |
| `gemini_brainstorm` | Creative ideation and problem-solving | Gemini 3 Pro |

### Web & Knowledge
| Tool | Description | Default Model |
|------|-------------|---------------|
| `gemini_web_search` | Real-time search with Google grounding & citations | Gemini 2.5 Flash |
| `gemini_file_search` | RAG queries on uploaded documents | Gemini 2.5 Flash |
| `gemini_create_file_store` | Create document stores for RAG | - |
| `gemini_upload_file` | Upload files to stores (PDF, DOCX, code, etc.) | - |
| `gemini_list_file_stores` | List available document stores | - |

### Multi-Modal Generation
| Tool | Description | Models |
|------|-------------|--------|
| `gemini_generate_image` | Native image generation (up to 4K) | Gemini 3 Pro, 2.5 Flash |
| `gemini_generate_video` | Video with audio (4-8 sec, 720p/1080p) | Veo 3.1, Veo 3, Veo 2 |
| `gemini_text_to_speech` | Natural TTS with 30 voices | Gemini 2.5 Flash/Pro TTS |

## Quick Start

### Prerequisites

- Python 3.8+
- Claude Code CLI ([installation guide](https://claude.ai/code))
- Google Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Installation

**Option 1: Automatic Setup**

```bash
git clone https://github.com/marmyx77/gemini-mcp-pro.git
cd gemini-mcp-pro
./setup.sh YOUR_GEMINI_API_KEY
```

**Option 2: Manual Setup**

1. Install dependencies:
```bash
pip install google-genai
```

2. Create the MCP server directory:
```bash
mkdir -p ~/.claude-mcp-servers/gemini-mcp-pro
cp server.py ~/.claude-mcp-servers/gemini-mcp-pro/
```

3. Register with Claude Code:
```bash
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=YOUR_API_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/server.py
```

4. Restart Claude Code to activate.

### Verify Installation

```bash
claude mcp list
# Should show: gemini-mcp-pro
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

### Web Search

Access real-time information with citations:

```
"Search the web with Gemini for the latest React 19 features"
```

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
- And 22 more...

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
export GEMINI_API_KEY="your-api-key-here"
```

### Server Location

The server is installed at: `~/.claude-mcp-servers/gemini-mcp-pro/`

### Update API Key

```bash
# Option 1: Environment variable (recommended)
claude mcp remove gemini-mcp-pro
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=NEW_API_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/server.py

# Option 2: Re-run setup
./setup.sh NEW_API_KEY
```

## Troubleshooting

### MCP not showing up

```bash
# Check registration
claude mcp list

# Re-register
claude mcp remove gemini-mcp-pro
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=YOUR_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/server.py

# Restart Claude Code
```

### Connection errors

1. Verify your API key is valid at [AI Studio](https://aistudio.google.com/)
2. Check Python has the SDK: `pip show google-genai`
3. Test manually:
```bash
GEMINI_API_KEY=your_key python3 ~/.claude-mcp-servers/gemini-mcp-pro/server.py
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

## Credits

Inspired by [claude_code-gemini-mcp](https://github.com/RaiAnsar/claude_code-gemini-mcp) by RaiAnsar.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policies and how to report vulnerabilities.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built for the Claude Code community
