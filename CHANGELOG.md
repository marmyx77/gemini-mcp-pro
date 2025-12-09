# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.2] - 2025-12-09

### Security Fixes (Phase 1)
- **ReDoS Protection**: Fixed catastrophic backtracking vulnerabilities in SecretsSanitizer
  - All regex patterns now have bounded quantifiers (explicit max lengths)
  - Added `regex_timeout()` context manager with signal-based timeout (Unix)
  - Input size limit of 1MB for sanitization operations
  - Fail-open behavior on timeout (prioritizes availability)

- **XML Injection Prevention**: Replaced regex XML parser with `defusedxml`
  - Uses `defusedxml.ElementTree` to prevent XXE and billion laughs attacks
  - Regex fallback only for malformed LLM output
  - Strict whitelist validation for action types (create/modify/delete)
  - Path traversal blocking in generated file paths

- **Info Disclosure Fix**: Sanitized error messages in path validation
  - Error messages no longer expose filesystem paths
  - Generic "Access denied: path is outside allowed directory" message

### Fixed
- **Context Truncation Bug**: Conversation memory now prioritizes recent messages
  - Was incorrectly discarding recent messages when truncating
  - Now iterates newest→oldest, keeping recent context
  - Chronological order preserved in output

- **Video Generation Deadlock**: Removed async polling that caused FastMCP deadlock
  - `asyncio.run_coroutine_threadsafe().result()` blocked the event loop
  - Now uses sync `time.sleep()` polling instead
  - Video generation works correctly (tested with Veo 3.1)

### Security Fixes (Phase 2)
- **File Locking**: SafeFileWriter now uses `fcntl.flock()` on Unix
  - Prevents race conditions during concurrent file writes
  - 5-second timeout with `FileLockError` on failure
  - Automatic lock file cleanup
  - Windows fallback relies on atomic rename

- **Database Permissions**: SQLite database now has restrictive permissions
  - Database directory set to 0o700 (owner only)
  - Database file set to 0o600 (owner read/write)
  - WAL and SHM files also secured
  - Prevents other users from reading conversation history

- **Binary File Detection**: New `is_binary_file()` function
  - Detects binary files by extension (50+ types)
  - Magic byte signature detection (PNG, JPEG, PDF, ZIP, ELF, etc.)
  - Null byte presence check
  - UTF-8 validity check
  - `secure_read_file()` now rejects binary files by default

### Internal
- **Test Reorganization**: Renamed `tests/3.0b/` to `tests/integration/`
  - Clearer naming convention
  - Removed empty `tests/mocks/` directory
  - Added `tests/README.md` with documentation

### Dependencies
- Added `defusedxml>=0.7.1` to requirements

---

## [3.0.1] - 2025-12-08

### Security Hardening
- **Total Byte Limit**: `analyze_codebase` now enforces 5MB total limit across all files (prevents memory exhaustion DoS)
- **XML Sanitization**: `generate_code` now sanitizes XML output to prevent injection attacks
  - Removes control characters
  - Validates action types (only create/modify/delete)
  - Blocks path traversal in generated file paths

### Added
- **Dry-Run Mode**: New `dry_run` parameter for `gemini_generate_code`
  - Shows preview of files that would be created/modified
  - Displays code content without writing to disk
  - Shows whether target files already exist

- **Async Video Polling**: Video generation now supports async polling
  - Uses `asyncio.to_thread()` for non-blocking API calls
  - Falls back to sync polling if no event loop running
  - Better integration with async frameworks

### Deprecated
- **app/__main__.py**: Legacy JSON-RPC handler deprecated, use FastMCP server via `run.py`
- **app/services/memory.py**: In-memory conversation storage deprecated, use `PersistentConversationMemory`
- **server.py shim**: Backward compatibility shim deprecated, import from `app/` modules directly

All deprecated modules issue `DeprecationWarning` on import and will be removed in v4.0.0.

### Internal
- Version bumped in `pyproject.toml`, `app/__init__.py`, `app/core/config.py`
- Gemini analysis rated v3.0.1 as "Production-Grade Release"

See [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md) for planned v3.1.0 and v4.0.0 features.

---

## [3.0.0] - 2025-12-08

### BREAKING CHANGES
- **FastMCP Migration**: Now uses official MCP SDK (`mcp[cli]`) instead of manual JSON-RPC
- **Python 3.9+**: Minimum Python version increased from 3.8 to 3.9
- **Tool Names**: `mcp_ask_gemini` renamed to `ask_gemini` for consistency

### Added
- **FastMCP Server**: Full migration to official MCP Python SDK
  - Protocol-compliant tool registration with `@mcp.tool()` decorators
  - Automatic MCP handshake and message handling
  - 15 tools registered via FastMCP
  - `app/server.py` as the new FastMCP-based server

- **SQLite Persistence**: Conversation history survives server restarts
  - `~/.gemini-mcp-pro/conversations.db` SQLite database
  - Thread-safe operations with WAL mode and `threading.Lock`
  - Automatic TTL-based cleanup (configurable via `GEMINI_CONVERSATION_TTL_HOURS`)
  - `PersistentConversationMemory` class in `app/services/persistence.py`

- **Security Fixes**:
  - **Path Traversal**: Fixed in SafeFileWriter using `is_relative_to()`
  - **TOCTOU Race Condition**: Fixed in `secure_read_file()` using `fstat()` on open file descriptor
  - **DoS Protection**: 10MB max request size limit in JSON-RPC handler
  - **JSON-RPC Compliance**: Proper `-32700` parse error response
  - **Plugin Security**: Directory permission check prevents world-writable plugins

- **Modular Architecture**: Complete restructure from single-file to package-based architecture
  - `app/` package with organized submodules
  - `run.py` as lightweight entry point
  - Clear separation: core, services, tools, utils, schemas, middleware
  - Domain-based tool organization: `tools/text/`, `tools/code/`, `tools/media/`, `tools/web/`, `tools/rag/`

- **Backward Compatibility Shim**: `server.py` re-exports from `app/` modules
  - Existing code importing from `server` continues to work
  - Deprecation warnings planned for v4.0

- **Comprehensive Test Suite**: 118+ tests across 5 test files
  - `tests/3.0b/test_fastmcp_server.py` - FastMCP initialization, tool registration
  - `tests/3.0b/test_mcp_tools.py` - All 15 tool signatures and schemas
  - `tests/3.0b/test_sqlite_persistence.py` - SQLite persistence, thread safety
  - `tests/3.0b/test_security_v3.py` - Security features, path traversal prevention
  - `tests/3.0b/test_backward_compat.py` - Backward compatibility shim

- **Real MCP Tool Testing**: All 14 callable tools verified via live MCP calls
  - Outputs archived in `tests/3.0b/real_outputs/`
  - Generated media files (image, audio) verified

### Changed
- **Entry Point**: `server.py` → `run.py` + `app/` package
- **Installation**: Now copies `app/` directory and `run.py`
- **MCP Command**: Uses `run.py` instead of `server.py`
- **Dependencies**: Added `mcp[cli]>=1.0.0` to requirements

### Removed
- **Manual JSON-RPC**: Replaced by FastMCP SDK
- **In-Memory State**: Replaced by SQLite persistence

### Migration Guide
```bash
# Option 1: Fresh install (recommended)
./setup.sh YOUR_GEMINI_API_KEY

# Option 2: Manual update
pip install 'mcp[cli]>=1.0.0'
rm ~/.claude-mcp-servers/gemini-mcp-pro/server.py
cp -r app/ ~/.claude-mcp-servers/gemini-mcp-pro/
cp run.py pyproject.toml ~/.claude-mcp-servers/gemini-mcp-pro/

# Update MCP registration
claude mcp remove gemini-mcp-pro
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY=YOUR_KEY \
  -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/run.py
```

---

## [2.7.0] - 2025-12-08

### Added
- **Docker Production Setup**: Production-ready containerization
  - `Dockerfile` with non-root user, health check, environment config
  - `docker-compose.yml` with security hardening (no-new-privileges, read-only filesystem)
  - Resource limits (2 CPU, 2GB RAM)
  - Log rotation and volume mounts for workspace, logs, backups

- **Structured JSON Logging**: Container-friendly log format
  - New `GEMINI_LOG_FORMAT` environment variable ("json" or "text")
  - `StructuredLogger` class with JSON output to stderr
  - Request ID tracking for distributed tracing
  - Automatic secrets sanitization in log output
  - Compatible with ELK, CloudWatch, Datadog log aggregation

### Enhanced
- `log_activity()`: Now supports `request_id` parameter and JSON format
- `log_progress()`: Now supports JSON format for container logging
- Imports consolidated at module top for cleaner code

### Internal
- New `LogRecord` dataclass for structured log entries
- UUID-based request ID generation per tool call

---

## [2.6.0] - 2025-12-08

### Added
- **Safe File Writing**: Atomic writes with automatic backup
  - `SafeFileWriter` class with temp file + rename pattern
  - Automatic backup creation (max 5 per file, timestamped)
  - Permission preservation after overwrite
  - Auto .gitignore for backup directory

- **Pydantic Input Validation**: Type-safe tool input validation
  - Schemas for 6 main tools (ask_gemini, generate_code, challenge, etc.)
  - Automatic type coercion and defaults
  - Clear error messages for invalid inputs
  - Integrated into `handle_tool_call()` with proper MCP error codes

- **Secrets Sanitizer**: Sensitive data detection and masking
  - 15+ patterns for API keys, tokens, passwords
  - Google, AWS, GitHub, Slack, generic patterns
  - Used in logging to prevent secret leakage

- **Test Suite Foundation**: 105 unit tests
  - Tests for SafeFileWriter, Pydantic schemas, SecretsSanitizer
  - Tests for path validation, line numbers, file references
  - Pytest fixtures for sandbox testing

### Fixed
- Pydantic validation now integrated into tool handler (previously implemented but not called)

---

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
