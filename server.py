#!/usr/bin/env python3
"""
gemini-mcp-pro v3.0.0 - Backward Compatibility Shim

DEPRECATED: This module is deprecated since v3.0.0.
Import directly from app/ modules instead:
    from app.core.security import validate_path, secure_read_file
    from app.core.security import SafeFileWriter, secure_write_file
    from app.services.gemini import client, types, MODELS
    from app.services.persistence import conversation_memory

This module will be removed in v4.0.0.
"""

import warnings

# Issue deprecation warning on import
warnings.warn(
    "server.py shim is deprecated since v3.0.0. "
    "Import directly from app/ modules instead: "
    "from app.core.security import validate_path; "
    "from app.services.gemini import client. "
    "This module will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from app modules for backward compatibility

# Configuration - aliased for backward compat
from app.core.config import config as _config

# Backward-compatible module-level constants
SANDBOX_ROOT = _config.sandbox_root
SANDBOX_ENABLED = _config.sandbox_enabled
MAX_FILE_SIZE = _config.max_file_size_bytes

# Security
from app.core.security import (
    validate_path,
    check_file_size,
    secure_read_file,
    SafeFileWriter,
    WriteResult,
    secure_write_file,
    SecretsSanitizer,
    secrets_sanitizer,
)

# Configuration
from app.core.config import config

# Logging
from app.core.logging import (
    log_activity,
    log_progress,
    structured_logger,
    StructuredLogger,
)

# Gemini client
from app.services.gemini import (
    client,
    types,
    MODELS,
    IMAGE_MODELS,
    VIDEO_MODELS,
    TTS_MODELS,
    TTS_VOICES,
    generate_with_fallback,
    is_available,
    get_error,
)

# Conversation memory
from app.services.persistence import (
    conversation_memory,
    ConversationTurn,
    PersistentConversationMemory,
)

# For legacy imports expecting ConversationThread from memory
from app.services.memory import (
    ConversationThread,
    ConversationMemory,
    CONVERSATION_TTL_HOURS,
    CONVERSATION_MAX_TURNS,
)

# Input validation
from app.schemas.inputs import validate_tool_input

# Utilities
from app.utils.file_refs import expand_file_references, add_line_numbers
from app.utils.tokens import estimate_tokens, check_prompt_size

# Code generation parser
from app.tools.code.generate_code import parse_generated_code

# Version
__version__ = "3.0.1"

# For backward compatibility with code that checks these at module level
MCP_PROMPT_SIZE_LIMIT = 60_000

# Entry point redirect
def main():
    """Run the MCP server (redirects to app.server.main)"""
    from app.server import main as server_main
    server_main()


if __name__ == "__main__":
    main()
