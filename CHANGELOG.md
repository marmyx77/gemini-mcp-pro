# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.5.0] - 2025-12-08

### Added
- **Dynamic Line Numbering**: @file references now include line numbers for better code navigation
  - Format: `  42│ actual code here`
  - Skipped for non-code files (.json, .md, .txt, .csv)
  - Makes code references more precise in Gemini responses

- **Code Generation Auto-Save**: `output_dir` parameter for `gemini_generate_code`
  - When specified, files are automatically saved to the directory
  - Returns summary with file paths and line counts
  - Respects sandbox security (files must be within allowed directories)
  - Supports nested directories (auto-creates as needed)

- **JSON More Info Protocol**: Gemini can request additional files during code generation
  - If Gemini needs more context, it responds with `{"need_files": ["path1", "path2"]}`
  - Server automatically fetches requested files and retries (max 1 retry)
  - Limits to 5 files per request to prevent abuse
  - Improves code generation accuracy by providing needed context

### Enhanced
- `gemini_generate_code`: Now supports auto-save with `output_dir` parameter
- `expand_file_references`: Now includes line numbers for code files

### Internal
- New helper functions: `parse_generated_code()`, `save_generated_files()`, `add_line_numbers()`

---

## [2.4.0] - 2025-12-08

### Added
- **Code Generation Tool**: `gemini_generate_code` for structured code generation
  - Returns XML-formatted output with file operations (create/modify)
  - Claude can parse and apply changes automatically
  - 3 style modes: production, prototype, minimal
  - 12 language options (auto-detect or specify)
  - Supports @file context for style matching
  - Best for UI components, boilerplate, and Gemini-strength tasks

### Usage Example
```
gemini_generate_code(
    prompt="Create a React login component with Tailwind CSS",
    context_files=["@src/App.tsx", "@package.json"],
    language="typescript",
    style="production"
)
```

### Output Format
```xml
<GENERATED_CODE>
<FILE action="create" path="src/components/Login.tsx">
// Complete component code...
</FILE>
</GENERATED_CODE>
```

---

## [2.3.0] - 2025-12-08

### Added
- **Challenge Tool**: `gemini_challenge` for critical thinking and "Devil's Advocate" analysis
  - Actively looks for flaws, risks, and problems in ideas/plans/code
  - 6 focus areas: general, security, performance, maintainability, scalability, cost
  - Structured output: Critical Flaws, Risks, Assumptions, Missing Considerations, Alternatives
  - Supports @file references for challenging code or documentation
  - Use before implementing to catch issues early

- **Activity Logging**: Professional logging system for tool usage monitoring
  - Separate log file at `~/.gemini-mcp-pro/activity.log`
  - Rotating file handler (10MB max, 5 backups) - never saturates disk
  - Logs: tool name, status (start/success/error), duration, details
  - Privacy-aware: truncates large values, no sensitive data logged
  - Configurable via environment variables

### Configuration (New Environment Variables)
- `GEMINI_ACTIVITY_LOG`: Enable/disable activity logging (default: true)
- `GEMINI_LOG_DIR`: Log directory path (default: ~/.gemini-mcp-pro)
- `GEMINI_LOG_MAX_BYTES`: Max log file size (default: 10MB)
- `GEMINI_LOG_BACKUP_COUNT`: Number of backup files (default: 5)

### Usage Example
```
# Challenge an architecture decision
gemini_challenge(
    statement="We'll use a microservices architecture with 12 services",
    context="Small team of 3 developers, MVP in 2 months",
    focus="scalability"
)

# Challenge code before implementation
gemini_challenge(
    statement="@src/auth.py",
    focus="security"
)
```

---

## [2.2.0] - 2025-12-08

### Added
- **Path Sandboxing**: Security feature to prevent directory traversal attacks
  - `validate_path()`: Ensures file access stays within sandbox root
  - Resolves symlinks to prevent bypass attacks
  - Blocks access to sensitive system files (e.g., `/etc/passwd`)
  - Configurable via `GEMINI_SANDBOX_ROOT` and `GEMINI_SANDBOX_ENABLED`

- **Pre-check File Size**: Rejects oversized files BEFORE reading them
  - `check_file_size()`: Fast file size validation
  - `secure_read_file()`: Combined path + size validation
  - Prevents memory exhaustion and context overflow
  - Configurable via `GEMINI_MAX_FILE_SIZE`

### Security
- All @file references now validate paths against sandbox
- Directory traversal patterns (`../`) are blocked
- Large files are rejected with helpful error messages

### Configuration (New Environment Variables)
- `GEMINI_SANDBOX_ROOT`: Root directory for file access (default: current working directory)
- `GEMINI_SANDBOX_ENABLED`: Enable/disable sandboxing (default: true)
- `GEMINI_MAX_FILE_SIZE`: Maximum file size in bytes (default: 102400 = 100KB)

---

## [2.1.0] - 2025-12-08

### Added
- **Codebase Analysis Tool**: `gemini_analyze_codebase` for large-scale code analysis
  - Leverages Gemini's 1M token context window (vs Claude's ~200K)
  - Analyze 50+ files at once with glob pattern support
  - 6 analysis types: architecture, security, refactoring, documentation, dependencies, general
  - Supports conversation memory for iterative analysis
  - Auto-skips binary files and oversized files (>100KB)

- **Tool Disabling**: `GEMINI_DISABLED_TOOLS` env var to reduce context bloat
  - Example: `GEMINI_DISABLED_TOOLS=gemini_generate_video,gemini_text_to_speech`

- **Infrastructure Improvements**:
  - `estimate_tokens()`: Token estimation function (~4 chars/token)
  - `check_prompt_size()`: Prevents MCP transport errors (60K char limit)
  - Prompt size validation on all text-accepting tools

### Configuration (New Environment Variables)
- `GEMINI_DISABLED_TOOLS`: Comma-separated list of tools to disable

### Usage Example
```
# Analyze entire project architecture
gemini_analyze_codebase(
    prompt="Explain the architecture and key design decisions",
    files=["src/**/*.py", "tests/*.py"],
    analysis_type="architecture"
)

# Follow-up with memory
gemini_analyze_codebase(
    prompt="What refactoring opportunities do you see?",
    files=["src/**/*.py"],
    analysis_type="refactoring",
    continuation_id="<id-from-previous>"
)
```

---

## [2.0.0] - 2025-12-08

### Added
- **Conversation Memory**: Multi-turn conversations with Gemini via `continuation_id`
  - Gemini "remembers" previous context across multiple calls
  - Automatic TTL-based cleanup (3 hours default)
  - Thread-safe in-memory storage with background cleanup
  - Max 50 turns per conversation thread
  - File reference deduplication across turns
  - Response includes `continuation_id` for subsequent calls

### Configuration (Environment Variables)
- `GEMINI_CONVERSATION_TTL_HOURS`: TTL for threads (default: 3)
- `GEMINI_CONVERSATION_MAX_TURNS`: Max turns per thread (default: 50)

### Usage Example
```
# First call - starts new conversation
ask_gemini("Analyze @auth.py for security issues")
# Response: "Found potential SQL injection..." + continuation_id: abc-123

# Second call - continues conversation (Gemini remembers!)
ask_gemini("How do I fix the SQL injection?", continuation_id="abc-123")
# Response: "Based on the auth.py I analyzed earlier, you should..."
```

## [1.3.0] - 2025-12-08

### Added
- **@File References**: Include file contents in prompts using @ syntax
  - `@file.py` - Single file
  - `@src/main.py` - Path with directories
  - `@*.py` - Glob patterns
  - `@src/**/*.ts` - Recursive glob patterns
  - `@.` - Current directory listing
- Supported in: `ask_gemini`, `gemini_brainstorm`, `gemini_code_review`
- Smart email detection (user@example.com not expanded)
- File size limits: 50KB single files, 10KB per file for globs (max 10 files)

### Credits
- @file syntax inspired by [gemini-mcp-tool](https://github.com/jamubc/gemini-mcp-tool) by jamubc

## [1.2.0] - 2025-12-08

### Added
- **Advanced Brainstorming**: `gemini_brainstorm` now supports 6 methodologies:
  - `auto`: AI selects best approach
  - `divergent`: Generate many ideas without filtering
  - `convergent`: Refine and improve existing concepts
  - `scamper`: Systematic creative triggers (Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse)
  - `design-thinking`: Human-centered approach
  - `lateral`: Unexpected connections and assumption challenges
- New brainstorm parameters: `domain`, `constraints`, `idea_count`, `include_analysis`
- **Quota Fallback**: Automatic Pro→Flash fallback when quota exceeded
- **Progress Logging**: Real-time status updates for long-running operations (video, image, upload)

### Changed
- `gemini_brainstorm` schema expanded with new parameters
- Internal refactoring with `generate_with_fallback()` helper function

### Credits
- Brainstorming methodologies inspired by [gemini-mcp-tool](https://github.com/jamubc/gemini-mcp-tool) by jamubc

## [1.1.0] - 2025-12-08

### Added
- `gemini_analyze_image`: New tool for image analysis using Gemini vision capabilities
  - Supports PNG, JPG, JPEG, GIF, WEBP formats
  - Use cases: describe images, extract text (OCR), identify objects, answer questions
  - Default model: Gemini 2.5 Flash (reliable vision)
  - Optional: Gemini 3 Pro (experimental)

## [1.0.0] - 2025-12-08

### Added
- Initial release with 11 tools across 3 categories

#### Text & Reasoning
- `ask_gemini`: Text generation with optional thinking mode
- `gemini_code_review`: Code analysis with security, performance, and quality focus
- `gemini_brainstorm`: Creative ideation and problem-solving

#### Web & Knowledge
- `gemini_web_search`: Real-time search with Google grounding and citations
- `gemini_file_search`: RAG queries on uploaded documents
- `gemini_create_file_store`: Create document stores for RAG
- `gemini_upload_file`: Upload files to stores (PDF, DOCX, code, etc.)
- `gemini_list_file_stores`: List available document stores

#### Multi-Modal Generation
- `gemini_generate_image`: Native image generation (up to 4K with Gemini 3 Pro)
- `gemini_generate_video`: Video generation with Veo 3.1 (720p/1080p, native audio)
- `gemini_text_to_speech`: TTS with 30 voices, single and multi-speaker support
