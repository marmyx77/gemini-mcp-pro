#!/usr/bin/env python3
"""
gemini-mcp-pro v2.5.0
Full-featured MCP server for Google Gemini: text generation with thinking mode,
web search, RAG, image analysis, image generation, video generation, text-to-speech.
Features: conversation memory, @file references with line numbers, codebase analysis (1M context),
path sandboxing, challenge tool, code generation with auto-save, activity logging, Pro→Flash fallback.
"""

import json
import sys
import os
import base64
import time
import wave
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, List, Literal
from enum import Enum

# Pydantic v2 for input validation (v2.6.0)
try:
    from pydantic import BaseModel, Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False

# Ensure unbuffered output for MCP JSON-RPC communication
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    # Fallback for older Python versions
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

__version__ = "2.6.0"

# Model mapping - Gemini 3 Pro prioritized for advanced reasoning
# Use "fast" for high-volume, low-reasoning tasks
MODELS = {
    "pro": "gemini-3-pro-preview",       # Best for reasoning, coding, complex tasks
    "flash": "gemini-2.5-flash",          # Balanced speed/quality for standard tasks
    "fast": "gemini-2.5-flash",           # High-volume, simple tasks (same as flash, lower cost tier)
}

# Image models
IMAGE_MODELS = {
    "pro": "gemini-3-pro-image-preview",  # High quality, 4K, thinking mode
    "flash": "gemini-2.5-flash-image",    # Fast generation
}

# Video models - Veo 3.1 for state-of-the-art video generation with audio
VIDEO_MODELS = {
    "veo31": "veo-3.1-generate-preview",       # Best quality, 8s, 720p/1080p, audio
    "veo31_fast": "veo-3.1-fast-generate-preview",  # Faster, optimized for speed
    "veo3": "veo-3.0-generate-001",            # Stable, 8s with audio
    "veo3_fast": "veo-3.0-fast-generate-001",  # Fast stable version
    "veo2": "veo-2.0-generate-001",            # Legacy, no audio
}

# TTS models - Native text-to-speech
TTS_MODELS = {
    "flash": "gemini-2.5-flash-preview-tts",  # Fast TTS
    "pro": "gemini-2.5-pro-preview-tts",      # Higher quality TTS
}

# Available TTS voices with their characteristics
TTS_VOICES = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm",
}


# =============================================================================
# PYDANTIC INPUT SCHEMAS (v2.6.0)
# =============================================================================
# Type-safe validation for tool inputs with automatic JSON Schema generation

if PYDANTIC_AVAILABLE:
    class ThinkingLevel(str, Enum):
        """Gemini thinking mode levels."""
        OFF = "off"
        LOW = "low"
        HIGH = "high"

    class CodeStyle(str, Enum):
        """Code generation style options."""
        PRODUCTION = "production"
        PROTOTYPE = "prototype"
        MINIMAL = "minimal"

    class AnalysisType(str, Enum):
        """Codebase analysis focus areas."""
        ARCHITECTURE = "architecture"
        SECURITY = "security"
        REFACTORING = "refactoring"
        DOCUMENTATION = "documentation"
        DEPENDENCIES = "dependencies"
        GENERAL = "general"

    class ChallengeFocus(str, Enum):
        """Devil's advocate critique focus areas."""
        GENERAL = "general"
        SECURITY = "security"
        PERFORMANCE = "performance"
        MAINTAINABILITY = "maintainability"
        SCALABILITY = "scalability"
        COST = "cost"

    class AskGeminiInput(BaseModel):
        """Schema for ask_gemini tool input."""
        prompt: str = Field(
            ...,
            min_length=1,
            max_length=100000,
            description="The question or prompt for Gemini"
        )
        model: Literal["pro", "flash", "fast"] = Field(
            default="pro",
            description="Model selection: pro (best reasoning), flash (balanced), fast (high volume)"
        )
        temperature: float = Field(
            default=0.5,
            ge=0.0,
            le=1.0,
            description="Sampling temperature (0.0 = deterministic, 1.0 = creative)"
        )
        thinking_level: ThinkingLevel = Field(
            default=ThinkingLevel.OFF,
            description="Thinking depth: off, low (fast), high (deep reasoning)"
        )
        include_thoughts: bool = Field(
            default=False,
            description="Include reasoning process in output"
        )
        continuation_id: Optional[str] = Field(
            default=None,
            description="Thread ID for conversation continuity"
        )

    class GenerateCodeInput(BaseModel):
        """Schema for gemini_generate_code tool input."""
        prompt: str = Field(
            ...,
            min_length=1,
            description="What code to generate"
        )
        context_files: Optional[List[str]] = Field(
            default=None,
            description="Files to include as context (@file syntax)"
        )
        language: Literal[
            "auto", "typescript", "javascript", "python",
            "rust", "go", "java", "cpp", "csharp", "html", "css", "sql"
        ] = Field(default="auto", description="Target language")
        style: CodeStyle = Field(
            default=CodeStyle.PRODUCTION,
            description="Code style: production (full), prototype (basic), minimal (bare)"
        )
        model: Literal["pro", "flash"] = Field(
            default="pro",
            description="Model selection"
        )
        output_dir: Optional[str] = Field(
            default=None,
            description="Directory to auto-save generated files"
        )

        @field_validator('context_files', mode='before')
        @classmethod
        def handle_null_context_files(cls, v):
            """Handle null from MCP protocol."""
            return v or []

    class ChallengeInput(BaseModel):
        """Schema for gemini_challenge tool input."""
        statement: str = Field(
            ...,
            min_length=1,
            description="The idea/plan/code to critique"
        )
        context: str = Field(
            default="",
            description="Background context or constraints"
        )
        focus: ChallengeFocus = Field(
            default=ChallengeFocus.GENERAL,
            description="Focus area for critique"
        )

    class AnalyzeCodebaseInput(BaseModel):
        """Schema for gemini_analyze_codebase tool input."""
        prompt: str = Field(
            ...,
            min_length=1,
            description="Analysis task or question"
        )
        files: List[str] = Field(
            ...,
            min_length=1,
            description="File paths or glob patterns to analyze"
        )
        analysis_type: AnalysisType = Field(
            default=AnalysisType.GENERAL,
            description="Type of analysis to perform"
        )
        model: Literal["pro", "flash"] = Field(
            default="pro",
            description="Model selection"
        )
        continuation_id: Optional[str] = Field(
            default=None,
            description="Thread ID for iterative analysis"
        )

    class CodeReviewInput(BaseModel):
        """Schema for gemini_code_review tool input."""
        code: str = Field(
            ...,
            min_length=1,
            description="Code to review"
        )
        focus: Literal["security", "performance", "readability", "bugs", "general"] = Field(
            default="general",
            description="Focus area for review"
        )
        model: Literal["pro", "flash"] = Field(
            default="pro",
            description="Model selection"
        )

    class BrainstormInput(BaseModel):
        """Schema for gemini_brainstorm tool input."""
        topic: str = Field(
            ...,
            min_length=1,
            description="Topic or challenge to brainstorm"
        )
        domain: Optional[str] = Field(
            default=None,
            description="Domain context: software, business, creative, etc."
        )
        methodology: Literal[
            "auto", "divergent", "convergent", "scamper", "design-thinking", "lateral"
        ] = Field(default="auto", description="Brainstorming framework")
        idea_count: int = Field(
            default=10,
            ge=1,
            le=50,
            description="Target number of ideas"
        )
        constraints: Optional[str] = Field(
            default=None,
            description="Known limitations: budget, time, technical, legal, etc."
        )
        context: str = Field(
            default="",
            description="Additional context or background"
        )
        include_analysis: bool = Field(
            default=True,
            description="Include feasibility, impact, and innovation scores"
        )

    def validate_tool_input(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate tool input using Pydantic schema.

        Args:
            tool_name: Name of the tool (e.g., "ask_gemini")
            args: Input arguments from MCP

        Returns:
            Validated and coerced arguments (enums serialized to strings)

        Raises:
            ValueError: If validation fails
        """
        schema_map = {
            "ask_gemini": AskGeminiInput,
            "gemini_generate_code": GenerateCodeInput,
            "gemini_challenge": ChallengeInput,
            "gemini_analyze_codebase": AnalyzeCodebaseInput,
            "gemini_code_review": CodeReviewInput,
            "gemini_brainstorm": BrainstormInput,
        }

        schema_class = schema_map.get(tool_name)
        if not schema_class:
            return args  # No schema for this tool, pass through

        try:
            validated = schema_class(**args)
            # Use mode='json' to serialize enums to their string values
            return validated.model_dump(mode='json')
        except Exception as e:
            raise ValueError(f"Invalid input for {tool_name}: {e}")

else:
    # Pydantic not available - provide stub
    def validate_tool_input(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stub when Pydantic is not available."""
        return args


# =============================================================================
# SECRETS SANITIZER (v2.6.0)
# =============================================================================
# Detect and mask sensitive data in logs and outputs

import re


class SecretsSanitizer:
    """
    Detect and mask sensitive data in logs and outputs.

    Patterns detected:
    - API keys (Google, AWS, GitHub, generic)
    - JWT tokens
    - Bearer tokens
    - Private keys
    - Passwords in URLs
    - Connection strings

    Usage:
        sanitizer = SecretsSanitizer()
        safe_text = sanitizer.sanitize("My key is AIzaXXXXXXXX...")
        detected = sanitizer.detect(text)  # Returns ['GOOGLE_API_KEY']
    """

    # IMPORTANT: More specific patterns MUST come before generic ones
    # Order: JWT/specific tokens → API keys → Private keys → URL → Generic
    PATTERNS = [
        # JWT tokens (three base64-encoded parts) - FIRST (very specific format)
        (r'eyJ[a-zA-Z0-9\-_]+\.eyJ[a-zA-Z0-9\-_]+\.[a-zA-Z0-9\-_]+', 'JWT_TOKEN'),
        # Private keys (PEM format headers)
        (r'-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----', 'PRIVATE_KEY'),
        # Google/Gemini API keys (AIza format)
        (r'AIza[0-9A-Za-z\-_]{35}', 'GOOGLE_API_KEY'),
        # AWS Access Keys (AKIA format)
        (r'AKIA[0-9A-Z]{16}', 'AWS_ACCESS_KEY'),
        # GitHub tokens (specific prefixes)
        (r'ghp_[a-zA-Z0-9]{36}', 'GITHUB_PAT'),
        (r'gho_[a-zA-Z0-9]{36}', 'GITHUB_OAUTH'),
        (r'ghu_[a-zA-Z0-9]{36}', 'GITHUB_USER_TOKEN'),
        (r'ghs_[a-zA-Z0-9]{36}', 'GITHUB_SERVER_TOKEN'),
        (r'ghr_[a-zA-Z0-9]{36}', 'GITHUB_REFRESH_TOKEN'),
        # Anthropic API keys
        (r'sk-ant-[a-zA-Z0-9\-_]{40,}', 'ANTHROPIC_API_KEY'),
        # OpenAI API keys
        (r'sk-[a-zA-Z0-9]{48}', 'OPENAI_API_KEY'),
        # Slack tokens
        (r'xox[baprs]-[0-9a-zA-Z\-]{10,}', 'SLACK_TOKEN'),
        # Bearer tokens
        (r'(?i)bearer\s+[a-zA-Z0-9\-_.]+', 'BEARER_TOKEN'),
        # Password in URLs (http://user:pass@host)
        (r'(?i)://[^:]+:([^@]{3,})@', 'URL_PASSWORD'),
        # AWS Secret Keys (generic 40-char base64)
        (r'(?i)(aws_secret|secret_key)["\s:=]+["\']?([A-Za-z0-9/+=]{40})["\']?', 'AWS_SECRET_KEY'),
        # Generic API key patterns (key=value, key: value) - NEAR END
        (r'(?i)(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9\-_]{20,})["\']?', 'API_KEY'),
        # Generic secrets (password, secret, token in config) - LAST (most generic)
        (r'(?i)(password|passwd|secret)["\s:=]+["\']?([^\s"\']{8,})["\']?', 'GENERIC_SECRET'),
    ]

    def __init__(self):
        """Compile regex patterns for efficiency."""
        self.compiled_patterns = [
            (re.compile(pattern), name)
            for pattern, name in self.PATTERNS
        ]

    def sanitize(self, text: str) -> str:
        """
        Replace all detected secrets with masked versions.

        Args:
            text: Input text potentially containing secrets

        Returns:
            Text with secrets replaced by [REDACTED_TYPE]
        """
        if not text:
            return text

        result = text
        for pattern, name in self.compiled_patterns:
            result = pattern.sub(f'[REDACTED_{name}]', result)
        return result

    def detect(self, text: str) -> List[str]:
        """
        Return list of detected secret types (without exposing values).

        Args:
            text: Input text to scan

        Returns:
            List of secret type names detected (e.g., ['GOOGLE_API_KEY', 'JWT_TOKEN'])
        """
        if not text:
            return []

        detected = []
        for pattern, name in self.compiled_patterns:
            if pattern.search(text):
                detected.append(name)
        return detected

    def has_secrets(self, text: str) -> bool:
        """
        Quick check if text contains any detectable secrets.

        Args:
            text: Input text to scan

        Returns:
            True if any secret pattern matches
        """
        if not text:
            return False

        for pattern, _ in self.compiled_patterns:
            if pattern.search(text):
                return True
        return False


# Global instance for use across the application
secrets_sanitizer = SecretsSanitizer()


# Initialize Gemini
GEMINI_AVAILABLE = False
GEMINI_ERROR = ""
client = None

try:
    from google import genai
    from google.genai import types

    API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        GEMINI_ERROR = "Please set GEMINI_API_KEY environment variable"
    else:
        client = genai.Client(api_key=API_KEY)
        GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_ERROR = "google-genai SDK not installed. Run: pip install google-genai"
except Exception:
    # Don't expose internal error details that might leak sensitive info
    GEMINI_ERROR = "Failed to initialize Gemini client. Check your API key."


def log_progress(message: str):
    """Log progress messages to stderr for long-running operations"""
    print(f"[gemini-mcp-pro] {message}", file=sys.stderr, flush=True)


def send_response(response: Dict[str, Any]):
    """Send a JSON-RPC response"""
    print(json.dumps(response), flush=True)


def generate_with_fallback(model_id: str, contents: Any, config: Any = None,
                           operation: str = "request") -> Any:
    """
    Call Gemini API with automatic fallback from Pro to Flash on quota errors.

    Args:
        model_id: The model to use (e.g., "gemini-3-pro-preview")
        contents: The content to send to the model
        config: Optional GenerateContentConfig
        operation: Description of the operation for logging

    Returns:
        The API response

    Raises:
        Exception: If both Pro and Flash fail
    """
    try:
        if config:
            return client.models.generate_content(model=model_id, contents=contents, config=config)
        else:
            return client.models.generate_content(model=model_id, contents=contents)
    except Exception as e:
        error_msg = str(e).lower()
        # Check for quota/rate limit errors and if we're using a Pro model
        if ("quota" in error_msg or "rate" in error_msg or "resource" in error_msg) and "pro" in model_id.lower():
            log_progress(f"⚠️ {operation}: Pro model quota exceeded, falling back to Flash...")
            flash_model = MODELS["flash"]
            try:
                if config:
                    response = client.models.generate_content(model=flash_model, contents=contents, config=config)
                else:
                    response = client.models.generate_content(model=flash_model, contents=contents)
                log_progress(f"✅ {operation}: Completed with Flash fallback")
                return response
            except Exception as fallback_error:
                raise Exception(f"Both Pro and Flash failed. Pro error: {str(e)}. Flash error: {str(fallback_error)}")
        raise


import re
import glob as glob_module

def add_line_numbers(content: str, start_line: int = 1) -> str:
    """
    Add line numbers to content for better code references.

    Format: "  42│ actual code here"

    Args:
        content: The text content to number
        start_line: Starting line number (default 1)

    Returns:
        Content with line numbers prefixed
    """
    lines = content.split('\n')
    max_line_num = start_line + len(lines) - 1
    width = len(str(max_line_num))

    numbered_lines = []
    for i, line in enumerate(lines):
        line_num = start_line + i
        numbered_lines.append(f"{line_num:>{width}}│ {line}")

    return '\n'.join(numbered_lines)


def expand_file_references(text: str, base_path: str = None, add_lines: bool = True) -> str:
    """
    Expand @file references in text by replacing them with file contents.

    Supports:
    - @file.py - Single file
    - @src/main.py - Path with directories
    - @*.py - Glob patterns
    - @src/**/*.ts - Recursive glob patterns
    - @. - Current directory listing

    Args:
        text: Text containing @file references
        base_path: Base path for relative file references (defaults to cwd)
        add_lines: If True, add line numbers to file contents (v2.5.0)

    Returns:
        Text with @file references replaced by file contents
    """
    if not base_path:
        base_path = os.getcwd()

    # Pattern to match @references (not emails)
    # Matches @path but not user@domain.com
    pattern = r'(?<![a-zA-Z0-9])@([^\s@]+)'

    def replace_reference(match):
        ref = match.group(1)
        full_path = os.path.join(base_path, ref) if not os.path.isabs(ref) else ref

        # Handle @. for current directory listing
        if ref == '.':
            try:
                # v2.2.0: Validate base_path is within sandbox
                safe_base = validate_path(base_path)
                files = os.listdir(safe_base)
                return f"\n**Directory listing ({base_path}):**\n" + "\n".join(f"- {f}" for f in sorted(files)[:50])
            except PermissionError as e:
                return f"[Security error: {e}]"
            except Exception as e:
                return f"[Error listing directory: {e}]"

        # Handle glob patterns
        if '*' in ref:
            try:
                matched_files = glob_module.glob(full_path, recursive=True)
                if not matched_files:
                    return f"[No files matched pattern: {ref}]"

                result_parts = []
                for file_path in sorted(matched_files)[:10]:  # Limit to 10 files
                    if os.path.isfile(file_path):
                        try:
                            # v2.2.0: Validate path and check size
                            safe_path = validate_path(file_path)
                            size_err = check_file_size(safe_path, 10000)  # 10KB limit for glob
                            if size_err:
                                result_parts.append(f"\n**File: {file_path}**\n[Skipped: {size_err['message']}]")
                                continue

                            with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                            # v2.5.0: Add line numbers for better code references
                            if add_lines and not file_path.endswith(('.json', '.md', '.txt', '.csv')):
                                content = add_line_numbers(content)
                            result_parts.append(f"\n**File: {file_path}**\n```\n{content}\n```")
                        except PermissionError as e:
                            result_parts.append(f"\n**File: {file_path}**\n[Security error: {e}]")
                        except Exception as e:
                            result_parts.append(f"\n**File: {file_path}**\n[Error reading: {e}]")

                if len(matched_files) > 10:
                    result_parts.append(f"\n... and {len(matched_files) - 10} more files")

                return "\n".join(result_parts)
            except Exception as e:
                return f"[Error with glob pattern {ref}: {e}]"

        # Handle single file
        if os.path.isfile(full_path):
            try:
                # v2.2.0: Validate path and check size
                safe_path = validate_path(full_path)
                size_err = check_file_size(safe_path, 50000)  # 50KB limit for single files
                if size_err:
                    return f"\n**File: {ref}**\n[Skipped: {size_err['message']}]"

                with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                # v2.5.0: Add line numbers for better code references
                if add_lines and not ref.endswith(('.json', '.md', '.txt', '.csv')):
                    content = add_line_numbers(content)
                return f"\n**File: {ref}**\n```\n{content}\n```"
            except PermissionError as e:
                return f"[Security error: {e}]"
            except Exception as e:
                return f"[Error reading {ref}: {e}]"

        # Handle directory
        if os.path.isdir(full_path):
            try:
                # v2.2.0: Validate directory path
                safe_path = validate_path(full_path)
                files = os.listdir(safe_path)
                return f"\n**Directory: {ref}**\n" + "\n".join(f"- {f}" for f in sorted(files)[:50])
            except PermissionError as e:
                return f"[Security error: {e}]"
            except Exception as e:
                return f"[Error listing {ref}: {e}]"

        return f"[File not found: {ref}]"

    # Only process if there are @ references (excluding emails)
    if '@' in text:
        return re.sub(pattern, replace_reference, text)
    return text


# =============================================================================
# CONVERSATION MEMORY SYSTEM (v2.0.0)
# Enables multi-turn conversations with Gemini by maintaining context
# =============================================================================

import uuid
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Configuration
CONVERSATION_TTL_HOURS = int(os.environ.get("GEMINI_CONVERSATION_TTL_HOURS", "3"))
CONVERSATION_MAX_TURNS = int(os.environ.get("GEMINI_CONVERSATION_MAX_TURNS", "50"))
CONVERSATION_CLEANUP_INTERVAL = max(300, (CONVERSATION_TTL_HOURS * 3600) // 10)  # Min 5 min

# v2.1.0: Tool management and limits
DISABLED_TOOLS = [t.strip() for t in os.environ.get("GEMINI_DISABLED_TOOLS", "").split(",") if t.strip()]
MCP_PROMPT_SIZE_LIMIT = 60_000  # characters - prevents MCP transport errors

# v2.2.0: Security - Path sandboxing and file size limits
SANDBOX_ROOT = os.environ.get("GEMINI_SANDBOX_ROOT", os.getcwd())
MAX_FILE_SIZE_BYTES = int(os.environ.get("GEMINI_MAX_FILE_SIZE", str(100 * 1024)))  # 100KB default
SANDBOX_ENABLED = os.environ.get("GEMINI_SANDBOX_ENABLED", "true").lower() == "true"

# v2.3.0: Activity Logging - Separate log for tool usage monitoring
ACTIVITY_LOG_ENABLED = os.environ.get("GEMINI_ACTIVITY_LOG", "true").lower() == "true"
ACTIVITY_LOG_DIR = os.environ.get("GEMINI_LOG_DIR", os.path.expanduser("~/.gemini-mcp-pro"))
ACTIVITY_LOG_MAX_BYTES = int(os.environ.get("GEMINI_LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10MB default
ACTIVITY_LOG_BACKUP_COUNT = int(os.environ.get("GEMINI_LOG_BACKUP_COUNT", "5"))

# Initialize activity logger
activity_logger = None
if ACTIVITY_LOG_ENABLED:
    try:
        os.makedirs(ACTIVITY_LOG_DIR, exist_ok=True)
        activity_log_path = os.path.join(ACTIVITY_LOG_DIR, "activity.log")

        activity_logger = logging.getLogger("gemini_activity")
        activity_logger.setLevel(logging.INFO)
        activity_logger.propagate = False  # Don't propagate to root logger

        # Rotating file handler
        handler = RotatingFileHandler(
            activity_log_path,
            maxBytes=ACTIVITY_LOG_MAX_BYTES,
            backupCount=ACTIVITY_LOG_BACKUP_COUNT
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        activity_logger.addHandler(handler)

        log_progress(f"Activity logging enabled: {activity_log_path}")
    except Exception as e:
        log_progress(f"Warning: Could not initialize activity logging: {e}")
        activity_logger = None


def log_activity(tool_name: str, status: str, duration_ms: float = 0,
                 details: Dict[str, Any] = None, error: str = None):
    """
    Log tool activity for usage monitoring.

    Args:
        tool_name: Name of the tool called
        status: "start", "success", or "error"
        duration_ms: Execution time in milliseconds
        details: Additional details (truncated for privacy)
        error: Error message if status is "error"
    """
    if not activity_logger:
        return

    try:
        parts = [f"tool={tool_name}", f"status={status}"]

        if duration_ms > 0:
            parts.append(f"duration={duration_ms:.0f}ms")

        if details:
            # Truncate large values for privacy and log size
            safe_details = {}
            for k, v in details.items():
                if isinstance(v, str) and len(v) > 100:
                    safe_details[k] = f"{v[:100]}... ({len(v)} chars)"
                elif isinstance(v, list):
                    safe_details[k] = f"[{len(v)} items]"
                else:
                    safe_details[k] = v
            parts.append(f"details={json.dumps(safe_details)}")

        if error:
            parts.append(f"error={error[:200]}")

        activity_logger.info(" | ".join(parts))
    except Exception:
        pass  # Never fail on logging


def estimate_tokens(text: str) -> int:
    """Estimate token count for text (1 token ≈ 4 characters)"""
    return len(text) // 4


def check_prompt_size(text: str) -> Optional[Dict[str, str]]:
    """Check if prompt exceeds MCP transport limit.
    Returns error dict if too large, None if OK."""
    if len(text) > MCP_PROMPT_SIZE_LIMIT:
        return {
            "status": "error",
            "message": f"Prompt too large ({len(text):,} chars, limit {MCP_PROMPT_SIZE_LIMIT:,}). "
                      f"Save content to file and reference with @filename instead."
        }
    return None


# =============================================================================
# v2.2.0: SECURITY FUNCTIONS
# =============================================================================

def validate_path(file_path: str, allow_outside_sandbox: bool = False) -> str:
    """
    Validate and resolve a file path, ensuring it's within the sandbox.

    Security features:
    - Prevents directory traversal attacks (../)
    - Resolves symlinks to check actual destination
    - Blocks access outside SANDBOX_ROOT (unless disabled)

    Args:
        file_path: The path to validate (absolute or relative)
        allow_outside_sandbox: If True, skip sandbox check (for system files)

    Returns:
        The resolved absolute path if valid

    Raises:
        PermissionError: If path is outside sandbox or invalid
    """
    if not SANDBOX_ENABLED or allow_outside_sandbox:
        # Sandbox disabled - just resolve and return
        return os.path.abspath(file_path)

    try:
        # Resolve the path (handles .., symlinks, etc.)
        resolved = os.path.realpath(os.path.abspath(file_path))
        sandbox_resolved = os.path.realpath(os.path.abspath(SANDBOX_ROOT))

        # Check if resolved path is within sandbox
        if not resolved.startswith(sandbox_resolved + os.sep) and resolved != sandbox_resolved:
            raise PermissionError(
                f"Access denied: Path '{file_path}' resolves to '{resolved}' "
                f"which is outside sandbox '{sandbox_resolved}'"
            )

        return resolved

    except PermissionError:
        raise
    except Exception as e:
        raise PermissionError(f"Invalid path '{file_path}': {str(e)}")


def check_file_size(file_path: str, max_size: int = None) -> Optional[Dict[str, str]]:
    """
    Check if a file is too large to process before reading it.

    This prevents:
    - Memory exhaustion from huge files
    - Context window overflow
    - Wasted API costs on files that will be truncated anyway

    Args:
        file_path: Path to the file to check
        max_size: Maximum allowed size in bytes (defaults to MAX_FILE_SIZE_BYTES)

    Returns:
        None if file size is OK, error dict if too large
    """
    if max_size is None:
        max_size = MAX_FILE_SIZE_BYTES

    try:
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            return {
                "status": "error",
                "file": file_path,
                "size": file_size,
                "limit": max_size,
                "message": f"File too large: {os.path.basename(file_path)} is {file_size:,} bytes "
                          f"({file_size/1024:.1f}KB). Limit is {max_size:,} bytes ({max_size/1024:.0f}KB). "
                          f"Use @file syntax with specific line ranges or search for specific content."
            }
        return None
    except OSError as e:
        # File doesn't exist or can't be accessed - let the caller handle it
        return None


def secure_read_file(file_path: str, max_size: int = None) -> str:
    """
    Securely read a file with sandbox and size validation.

    Combines validate_path and check_file_size for a safe file read.

    Args:
        file_path: Path to the file to read
        max_size: Maximum allowed size in bytes

    Returns:
        File contents as string

    Raises:
        PermissionError: If path is outside sandbox
        ValueError: If file is too large
        FileNotFoundError: If file doesn't exist
    """
    # Validate path is within sandbox
    safe_path = validate_path(file_path)

    # Check file size before reading
    size_error = check_file_size(safe_path, max_size)
    if size_error:
        raise ValueError(size_error["message"])

    # Read the file
    with open(safe_path, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


# v2.6.0: SAFE FILE WRITER
# =============================================================================

@dataclass
class WriteResult:
    """Result of a safe file write operation."""
    success: bool
    path: str
    backup_path: Optional[str]
    content_hash: str
    error: Optional[str] = None
    preserved_permissions: bool = True


class SafeFileWriter:
    """
    Atomic file writer with backup and security features.

    v2.6.0 Security Features:
    - Atomic write: temp file + rename (prevents partial writes)
    - Automatic backup before overwrite (max 5 per file)
    - Permission preservation (chmod, ownership where possible)
    - Sandbox validation (all paths checked)
    - Symlink safety (resolves and validates destination)
    - Cross-platform support (handles Windows file locking)
    - Directory structure mirroring in backups
    - Auto-creates .gitignore in backup directory

    Usage:
        writer = SafeFileWriter(sandbox_root="/project")
        result = writer.write("src/app.py", "print('hello')")
        if result.success:
            print(f"Written to {result.path}, backup at {result.backup_path}")
    """

    BACKUP_DIR = ".gemini_backups"
    MAX_BACKUPS_PER_FILE = 5
    GITIGNORE_CONTENT = "# Auto-generated by gemini-mcp-pro\n*\n!.gitignore\n"

    def __init__(self, sandbox_root: str = None):
        """
        Initialize SafeFileWriter.

        Args:
            sandbox_root: Root directory for sandbox. Uses SANDBOX_ROOT if not specified.
        """
        self.sandbox_root = os.path.abspath(sandbox_root or SANDBOX_ROOT)
        self.backup_root = os.path.join(self.sandbox_root, self.BACKUP_DIR)

    def write(
        self,
        file_path: str,
        content: str,
        create_backup: bool = True,
        preserve_permissions: bool = True
    ) -> WriteResult:
        """
        Safely write content to file with atomic operation.

        Process:
        1. Validate path is in sandbox (handles symlinks)
        2. Create backup if file exists
        3. Capture original permissions
        4. Write to temp file in SAME directory (avoids EXDEV)
        5. Atomic rename to target
        6. Restore permissions

        Args:
            file_path: Target file path (absolute or relative to sandbox)
            content: Content to write
            create_backup: Whether to backup existing file (default: True)
            preserve_permissions: Whether to preserve original permissions (default: True)

        Returns:
            WriteResult with success status and details
        """
        import hashlib
        import stat
        import shutil

        # Make path absolute if relative
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.sandbox_root, file_path)

        # Validate path is in sandbox (this resolves symlinks)
        try:
            validated_path = validate_path(file_path)
        except PermissionError as e:
            return WriteResult(
                success=False,
                path=file_path,
                backup_path=None,
                content_hash="",
                error=str(e),
                preserved_permissions=False
            )

        # Calculate content hash
        content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

        # Check if file exists and capture permissions
        original_mode = None
        original_stat = None
        file_exists = os.path.exists(validated_path)

        if file_exists:
            try:
                original_stat = os.stat(validated_path)
                original_mode = stat.S_IMODE(original_stat.st_mode)
            except OSError:
                pass

        # Create backup if file exists
        backup_path = None
        if create_backup and file_exists:
            try:
                backup_path = self._create_backup(validated_path)
            except Exception as e:
                log_activity("safe_write", "warning",
                            details={"backup_failed": str(e), "path": file_path})
                # Continue without backup - user may want to proceed

        # Ensure parent directory exists
        parent_dir = os.path.dirname(validated_path)
        try:
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)
        except OSError as e:
            return WriteResult(
                success=False,
                path=file_path,
                backup_path=backup_path,
                content_hash=content_hash,
                error=f"Cannot create directory: {e}"
            )

        # Write to temp file in SAME directory (avoids cross-device issues)
        temp_path = None
        try:
            # Create temp file in same directory for atomic rename
            import tempfile
            fd, temp_path = tempfile.mkstemp(
                dir=parent_dir,
                prefix=f".{os.path.basename(validated_path)}.",
                suffix=".tmp"
            )

            try:
                # Write content
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is on disk

                # Restore permissions before rename
                if preserve_permissions and original_mode is not None:
                    try:
                        os.chmod(temp_path, original_mode)
                    except OSError:
                        pass  # Best effort

                # Atomic rename (os.replace is atomic and handles existing target)
                os.replace(temp_path, validated_path)
                temp_path = None  # Successfully renamed, don't cleanup

                return WriteResult(
                    success=True,
                    path=validated_path,
                    backup_path=backup_path,
                    content_hash=content_hash,
                    preserved_permissions=(original_mode is not None and preserve_permissions)
                )

            except Exception as e:
                # Close fd if not already closed
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise

        except PermissionError as e:
            # Windows file locking - try fallback method
            try:
                return self._write_fallback(
                    validated_path, content, content_hash, backup_path,
                    original_mode, preserve_permissions
                )
            except Exception as fallback_error:
                return WriteResult(
                    success=False,
                    path=file_path,
                    backup_path=backup_path,
                    content_hash=content_hash,
                    error=f"Write failed (tried fallback): {e} / {fallback_error}"
                )

        except Exception as e:
            return WriteResult(
                success=False,
                path=file_path,
                backup_path=backup_path,
                content_hash=content_hash,
                error=f"Write failed: {e}"
            )

        finally:
            # Cleanup temp file if it still exists (error case)
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    def _write_fallback(
        self,
        path: str,
        content: str,
        content_hash: str,
        backup_path: Optional[str],
        original_mode: Optional[int],
        preserve_permissions: bool
    ) -> WriteResult:
        """
        Fallback write method for Windows file locking.

        Uses in-place write instead of atomic rename.
        Less safe but handles "file in use" scenarios.
        """
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())

        if preserve_permissions and original_mode is not None:
            try:
                os.chmod(path, original_mode)
            except OSError:
                pass

        return WriteResult(
            success=True,
            path=path,
            backup_path=backup_path,
            content_hash=content_hash,
            preserved_permissions=(original_mode is not None and preserve_permissions)
        )

    def _create_backup(self, file_path: str) -> str:
        """
        Create timestamped backup of file.

        Preserves directory structure in backup folder.
        Returns backup path.
        """
        import shutil

        # Ensure backup directory exists with .gitignore
        self._ensure_backup_dir()

        # Get relative path from sandbox for directory structure
        try:
            rel_path = os.path.relpath(file_path, self.sandbox_root)
        except ValueError:
            # On Windows, relpath fails across drives
            rel_path = os.path.basename(file_path)

        # Create backup subdirectory mirroring source structure
        backup_subdir = os.path.join(self.backup_root, os.path.dirname(rel_path))
        if backup_subdir and not os.path.exists(backup_subdir):
            os.makedirs(backup_subdir, exist_ok=True)

        # Generate timestamped backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:20]  # Include microseconds
        backup_name = f"{os.path.basename(file_path)}.{timestamp}.bak"
        backup_path = os.path.join(backup_subdir, backup_name)

        # Copy file (preserves metadata)
        shutil.copy2(file_path, backup_path)

        # Rotate old backups
        self._rotate_backups(backup_subdir, os.path.basename(file_path))

        return backup_path

    def _ensure_backup_dir(self):
        """Ensure backup directory exists with proper .gitignore."""
        if not os.path.exists(self.backup_root):
            os.makedirs(self.backup_root, exist_ok=True)

        # Create .gitignore to prevent accidental commits
        gitignore_path = os.path.join(self.backup_root, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, 'w') as f:
                f.write(self.GITIGNORE_CONTENT)

    def _rotate_backups(self, backup_dir: str, original_filename: str):
        """Keep only MAX_BACKUPS_PER_FILE most recent backups per file."""
        import glob

        # Find all backups for this file
        pattern = os.path.join(backup_dir, f"{original_filename}.*.bak")
        backups = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)

        # Remove old backups
        for old_backup in backups[self.MAX_BACKUPS_PER_FILE:]:
            try:
                os.unlink(old_backup)
            except OSError:
                pass

    def restore_from_backup(self, backup_path: str) -> WriteResult:
        """
        Restore file from backup.

        Args:
            backup_path: Path to backup file

        Returns:
            WriteResult of the restoration
        """
        if not os.path.exists(backup_path):
            return WriteResult(
                success=False,
                path=backup_path,
                backup_path=None,
                content_hash="",
                error="Backup file not found"
            )

        # Extract original path from backup path
        try:
            rel_backup = os.path.relpath(backup_path, self.backup_root)
            # Remove timestamp.bak suffix
            parts = os.path.basename(rel_backup).rsplit('.', 2)
            if len(parts) >= 2:
                original_name = parts[0]
            else:
                original_name = parts[0]

            original_path = os.path.join(
                self.sandbox_root,
                os.path.dirname(rel_backup),
                original_name
            )

            # Read backup content
            with open(backup_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Write using safe write (creates new backup of current state)
            return self.write(original_path, content, create_backup=True)

        except Exception as e:
            return WriteResult(
                success=False,
                path=backup_path,
                backup_path=None,
                content_hash="",
                error=f"Restore failed: {e}"
            )

    def list_backups(self, file_path: str = None) -> List[Dict[str, Any]]:
        """
        List available backups.

        Args:
            file_path: If specified, list backups for this file only.
                      Otherwise list all backups.

        Returns:
            List of backup info dicts with path, original_file, timestamp, size
        """
        import glob

        if not os.path.exists(self.backup_root):
            return []

        backups = []

        if file_path:
            # Backups for specific file
            try:
                rel_path = os.path.relpath(file_path, self.sandbox_root)
            except ValueError:
                rel_path = os.path.basename(file_path)

            backup_dir = os.path.join(self.backup_root, os.path.dirname(rel_path))
            pattern = os.path.join(backup_dir, f"{os.path.basename(file_path)}.*.bak")
        else:
            # All backups
            pattern = os.path.join(self.backup_root, "**", "*.bak")

        for backup_path in glob.glob(pattern, recursive=True):
            try:
                stat_info = os.stat(backup_path)
                backups.append({
                    "path": backup_path,
                    "original_file": self._get_original_from_backup(backup_path),
                    "timestamp": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    "size": stat_info.st_size
                })
            except OSError:
                continue

        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)

    def _get_original_from_backup(self, backup_path: str) -> str:
        """Extract original file path from backup path."""
        try:
            rel_backup = os.path.relpath(backup_path, self.backup_root)
            parts = os.path.basename(rel_backup).rsplit('.', 2)
            original_name = parts[0] if parts else os.path.basename(rel_backup)
            return os.path.join(self.sandbox_root, os.path.dirname(rel_backup), original_name)
        except Exception:
            return backup_path


# Global SafeFileWriter instance
safe_file_writer = SafeFileWriter()


def secure_write_file(
    file_path: str,
    content: str,
    create_backup: bool = True
) -> WriteResult:
    """
    Convenience function for secure file writing.

    Uses global SafeFileWriter instance.

    Args:
        file_path: Target file path
        content: Content to write
        create_backup: Whether to backup existing file

    Returns:
        WriteResult with success status and details
    """
    return safe_file_writer.write(file_path, content, create_backup)


@dataclass
class ConversationTurn:
    """A single turn in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tool_name: str = None
    files_referenced: List[str] = field(default_factory=list)


@dataclass
class ConversationThread:
    """A conversation thread with multiple turns"""
    thread_id: str
    created_at: datetime
    last_activity: datetime
    turns: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if thread has expired based on TTL"""
        expiry = self.last_activity + timedelta(hours=CONVERSATION_TTL_HOURS)
        return datetime.now() > expiry

    def can_add_turn(self) -> bool:
        """Check if we can add more turns"""
        return len(self.turns) < CONVERSATION_MAX_TURNS

    def add_turn(self, role: str, content: str, tool_name: str = None,
                 files: List[str] = None) -> bool:
        """Add a turn to the conversation"""
        if not self.can_add_turn():
            return False

        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.now(),
            tool_name=tool_name,
            files_referenced=files or []
        )
        self.turns.append(turn)
        self.last_activity = datetime.now()
        return True

    def build_context(self, max_tokens: int = 800000) -> str:
        """
        Build conversation context for Gemini prompt.
        Prioritizes recent turns if token limit is approached.

        Args:
            max_tokens: Approximate token limit (chars/4)

        Returns:
            Formatted conversation history
        """
        if not self.turns:
            return ""

        # Estimate tokens (rough: 1 token ≈ 4 chars)
        max_chars = max_tokens * 4

        parts = [
            "=== CONVERSATION HISTORY ===",
            f"Thread: {self.thread_id}",
            f"Turns: {len(self.turns)}/{CONVERSATION_MAX_TURNS}",
            "",
            "Continue this conversation naturally. Reference previous context when relevant.",
            ""
        ]

        # Collect all unique files from conversation
        all_files = []
        seen_files = set()
        for turn in reversed(self.turns):  # Newest first for deduplication
            for f in turn.files_referenced:
                if f not in seen_files:
                    seen_files.add(f)
                    all_files.append(f)

        if all_files:
            parts.append("Files discussed in this conversation:")
            for f in all_files[:20]:  # Limit to 20 files
                parts.append(f"  - {f}")
            parts.append("")

        # Add turns (newest first for prioritization, then reverse for display)
        turn_texts = []
        total_chars = sum(len(p) for p in parts)

        for i, turn in enumerate(reversed(self.turns)):
            role_label = "You (Gemini)" if turn.role == "assistant" else "User request"
            turn_text = f"\n--- Turn {len(self.turns) - i} ({role_label}"
            if turn.tool_name:
                turn_text += f" via {turn.tool_name}"
            turn_text += f") ---\n{turn.content}\n"

            if total_chars + len(turn_text) > max_chars:
                parts.append(f"\n[Earlier {len(self.turns) - len(turn_texts)} turns omitted due to context limit]")
                break

            turn_texts.append((len(self.turns) - i, turn_text))
            total_chars += len(turn_text)

        # Reverse to show in chronological order
        for _, text in reversed(turn_texts):
            parts.append(text)

        parts.extend([
            "",
            "=== END CONVERSATION HISTORY ===",
            "",
            "IMPORTANT: You are continuing this conversation. Build upon previous context.",
            "Do not repeat previous analysis. Provide only NEW insights or direct answers.",
            ""
        ])

        return "\n".join(parts)


class ConversationMemory:
    """
    Thread-safe in-memory storage for conversation threads.
    Includes automatic TTL-based cleanup.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the memory storage"""
        self._threads: Dict[str, ConversationThread] = {}
        self._storage_lock = threading.Lock()
        self._shutdown = False

        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_worker,
            daemon=True,
            name="gemini-conversation-cleanup"
        )
        self._cleanup_thread.start()

        log_progress(f"Conversation memory initialized (TTL: {CONVERSATION_TTL_HOURS}h, max turns: {CONVERSATION_MAX_TURNS})")

    def create_thread(self, metadata: Dict[str, Any] = None) -> str:
        """Create a new conversation thread"""
        thread_id = str(uuid.uuid4())
        now = datetime.now()

        thread = ConversationThread(
            thread_id=thread_id,
            created_at=now,
            last_activity=now,
            metadata=metadata or {}
        )

        with self._storage_lock:
            self._threads[thread_id] = thread

        return thread_id

    def get_thread(self, thread_id: str) -> Optional[ConversationThread]:
        """Get a thread by ID, returns None if expired or not found"""
        with self._storage_lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return None

            if thread.is_expired():
                del self._threads[thread_id]
                return None

            return thread

    def add_turn(self, thread_id: str, role: str, content: str,
                 tool_name: str = None, files: List[str] = None) -> bool:
        """Add a turn to an existing thread"""
        thread = self.get_thread(thread_id)
        if thread is None:
            return False

        with self._storage_lock:
            return thread.add_turn(role, content, tool_name, files)

    def get_or_create_thread(self, continuation_id: str = None,
                             metadata: Dict[str, Any] = None) -> tuple:
        """
        Get existing thread or create new one.

        Returns:
            (thread_id, is_new, thread)
        """
        if continuation_id:
            thread = self.get_thread(continuation_id)
            if thread:
                return (continuation_id, False, thread)

        # Create new thread
        thread_id = self.create_thread(metadata)
        thread = self.get_thread(thread_id)
        return (thread_id, True, thread)

    def _cleanup_worker(self):
        """Background thread for cleaning up expired threads"""
        while not self._shutdown:
            time.sleep(CONVERSATION_CLEANUP_INTERVAL)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Remove all expired threads"""
        with self._storage_lock:
            expired = [tid for tid, t in self._threads.items() if t.is_expired()]
            for tid in expired:
                del self._threads[tid]

            if expired:
                log_progress(f"Cleaned up {len(expired)} expired conversation thread(s)")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics"""
        with self._storage_lock:
            return {
                "active_threads": len(self._threads),
                "ttl_hours": CONVERSATION_TTL_HOURS,
                "max_turns": CONVERSATION_MAX_TURNS
            }


# Global conversation memory instance
conversation_memory = ConversationMemory()


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough: 1 token ≈ 4 chars)"""
    return len(text) // 4


# =============================================================================
# END CONVERSATION MEMORY SYSTEM
# =============================================================================


def handle_initialize(request_id: Any) -> Dict[str, Any]:
    """Handle initialization"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "gemini-mcp-pro",
                "version": __version__
            }
        }
    }


def get_tools_list() -> List[Dict[str, Any]]:
    """Return available tools based on Gemini availability.

    Respects GEMINI_DISABLED_TOOLS env var to reduce context bloat.
    Example: GEMINI_DISABLED_TOOLS=gemini_generate_video,gemini_text_to_speech
    """
    if not GEMINI_AVAILABLE:
        return [{
            "name": "server_status",
            "description": f"Server error: {GEMINI_ERROR}",
            "inputSchema": {"type": "object", "properties": {}}
        }]

    all_tools = [
        {
            "name": "ask_gemini",
            "description": "Ask Gemini a question with optional model selection. Supports multi-turn conversations via continuation_id.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "The question or prompt"},
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash", "fast"],
                        "description": "Model: pro (Gemini 3 - best reasoning, default), flash (2.5 - balanced), fast (2.5 - high volume, low reasoning)",
                        "default": "pro"
                    },
                    "temperature": {
                        "type": "number",
                        "description": "Temperature 0.0-1.0",
                        "default": 0.5
                    },
                    "thinking_level": {
                        "type": "string",
                        "enum": ["off", "low", "high"],
                        "description": "Thinking level for Gemini 3 Pro: 'off' (no thinking), 'low' (fast), 'high' (deep reasoning). For 2.5 models uses budget instead.",
                        "default": "off"
                    },
                    "include_thoughts": {
                        "type": "boolean",
                        "description": "If true, returns thought summaries showing model's reasoning process",
                        "default": False
                    },
                    "continuation_id": {
                        "type": "string",
                        "description": "Thread ID to continue a previous conversation. Gemini will remember previous context. Omit to start a new conversation."
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_code_review",
            "description": "Have Gemini review code with specific focus. Uses Gemini 3 Pro for best reasoning.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "focus": {
                        "type": "string",
                        "description": "Focus area: security, performance, readability, bugs, general",
                        "default": "general"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Gemini 3 Pro - thorough analysis. flash: faster but less detailed",
                        "default": "pro"
                    }
                },
                "required": ["code"]
            }
        },
        {
            "name": "gemini_brainstorm",
            "description": "Advanced brainstorming with multiple methodologies. Uses Gemini 3 Pro for creative reasoning with structured frameworks like SCAMPER, Design Thinking, and more.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic or challenge to brainstorm"},
                    "context": {"type": "string", "description": "Additional context or background", "default": ""},
                    "methodology": {
                        "type": "string",
                        "enum": ["auto", "divergent", "convergent", "scamper", "design-thinking", "lateral"],
                        "description": "Brainstorming framework: auto (AI selects), divergent (many ideas), convergent (refine), scamper (creative triggers), design-thinking (human-centered), lateral (unexpected connections)",
                        "default": "auto"
                    },
                    "domain": {
                        "type": "string",
                        "description": "Domain context: software, business, creative, marketing, product, research, etc."
                    },
                    "constraints": {
                        "type": "string",
                        "description": "Known limitations: budget, time, technical, legal, etc."
                    },
                    "idea_count": {
                        "type": "integer",
                        "description": "Target number of ideas to generate",
                        "default": 10
                    },
                    "include_analysis": {
                        "type": "boolean",
                        "description": "Include feasibility, impact, and innovation scores for each idea",
                        "default": True
                    }
                },
                "required": ["topic"]
            }
        },
        {
            "name": "gemini_web_search",
            "description": "Search the web using Gemini with Google Search grounding. Returns answers with citations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro: Gemini 3 Pro - better synthesis. flash (default): faster for simple queries",
                        "default": "flash"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "gemini_create_file_store",
            "description": "Create a File Search Store for RAG. Use this before uploading files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Display name for the store"}
                },
                "required": ["name"]
            }
        },
        {
            "name": "gemini_upload_file",
            "description": "Upload a file to a File Search Store for RAG queries",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Local file path to upload"},
                    "store_name": {"type": "string", "description": "File Search Store name (from create_file_store)"}
                },
                "required": ["file_path", "store_name"]
            }
        },
        {
            "name": "gemini_file_search",
            "description": "Query documents in a File Search Store using RAG",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask about the documents"},
                    "store_name": {"type": "string", "description": "File Search Store name"}
                },
                "required": ["question", "store_name"]
            }
        },
        {
            "name": "gemini_analyze_image",
            "description": "Analyze an image using Gemini vision capabilities. Describe, extract text, identify objects, or answer questions about images.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Local file path to the image (supports PNG, JPG, JPEG, GIF, WEBP)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to do with the image: 'describe', 'extract text', or a specific question",
                        "default": "Describe this image in detail"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "flash (default): Gemini 2.5 Flash - reliable vision. pro: Gemini 3 Pro (experimental)",
                        "default": "flash"
                    }
                },
                "required": ["image_path"]
            }
        },
        {
            "name": "gemini_generate_image",
            "description": "Generate an image using Gemini native image generation. Defaults to Gemini 3 Pro for best quality. Use descriptive prompts (not keywords).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed image description. Be specific: describe scene, lighting, style, camera angle. Example: 'A photorealistic close-up portrait of an elderly ceramicist with warm lighting, captured with 85mm lens'"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Gemini 3 Pro - high quality, 4K, thinking mode. flash: Gemini 2.5 Flash - fast generation",
                        "default": "pro"
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                        "description": "Output aspect ratio",
                        "default": "1:1"
                    },
                    "image_size": {
                        "type": "string",
                        "enum": ["1K", "2K", "4K"],
                        "description": "Resolution (only for pro model). 1K=1024px, 2K=2048px, 4K=4096px",
                        "default": "2K"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save image (optional, returns base64 preview if not provided)"
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_list_file_stores",
            "description": "List all available File Search Stores",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "gemini_generate_video",
            "description": "Generate a video using Google Veo 3.1 with native audio. Creates 4-8 second 720p/1080p videos with realistic motion, dialogue, and sound effects. Use descriptive prompts including subject, action, style, camera motion.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed video description. Include: subject, action, style, camera motion, ambiance. For dialogue use quotes: 'Hello,' she said. For sounds describe explicitly: engine roaring, birds chirping."
                    },
                    "model": {
                        "type": "string",
                        "enum": ["veo31", "veo31_fast", "veo3", "veo3_fast", "veo2"],
                        "description": "veo31 (default): Best quality with audio. veo31_fast: Faster. veo3/veo3_fast: Stable versions. veo2: Legacy, no audio.",
                        "default": "veo31"
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "9:16"],
                        "description": "16:9 for landscape (default), 9:16 for portrait/vertical",
                        "default": "16:9"
                    },
                    "duration": {
                        "type": "integer",
                        "enum": [4, 6, 8],
                        "description": "Video duration in seconds. 8s required for 1080p.",
                        "default": 8
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["720p", "1080p"],
                        "description": "720p (default) or 1080p (Veo 3.1 only, requires 8s duration)",
                        "default": "720p"
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What NOT to include (e.g., 'cartoon, low quality, blurry'). Don't use 'no' or 'don't'."
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save video (.mp4). If not provided, saves to /tmp/"
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_text_to_speech",
            "description": "Convert text to speech using Gemini TTS. Supports single-speaker and multi-speaker (up to 2) audio with 30 voice options. Control style, tone, accent, and pace with natural language.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech. Include style instructions like 'Say cheerfully:' or 'Speaker1 sounds tired:'. For multi-speaker, format as 'Speaker1: text\\nSpeaker2: text'"
                    },
                    "voice": {
                        "type": "string",
                        "enum": ["Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"],
                        "description": "Voice for single-speaker. Popular: Kore (Firm), Puck (Upbeat), Charon (Informative), Aoede (Breezy), Sulafat (Warm)",
                        "default": "Kore"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["flash", "pro"],
                        "description": "flash (default): Fast TTS. pro: Higher quality",
                        "default": "flash"
                    },
                    "speakers": {
                        "type": "array",
                        "description": "For multi-speaker: [{\"name\": \"Speaker1\", \"voice\": \"Kore\"}, {\"name\": \"Speaker2\", \"voice\": \"Puck\"}]. Max 2 speakers.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "voice": {"type": "string"}
                            }
                        }
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save audio (.wav). If not provided, saves to /tmp/"
                    }
                },
                "required": ["text"]
            }
        },
        {
            "name": "gemini_analyze_codebase",
            "description": "Analyze large codebases using Gemini's 1M token context window. Perfect for architecture analysis, cross-file review, refactoring planning, and understanding complex projects. Supports 50+ files at once.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Analysis task: e.g., 'Explain the architecture', 'Find security issues', 'Identify refactoring opportunities', 'How does authentication work?'"
                    },
                    "files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file paths to analyze. Supports glob patterns: ['src/**/*.py', 'tests/*.py']. Max ~50 files recommended."
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["architecture", "security", "refactoring", "documentation", "dependencies", "general"],
                        "description": "Type of analysis to focus on",
                        "default": "general"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Best for complex analysis. flash: Faster for simpler tasks.",
                        "default": "pro"
                    },
                    "continuation_id": {
                        "type": "string",
                        "description": "Thread ID to continue iterative analysis. Gemini remembers previous findings."
                    }
                },
                "required": ["prompt", "files"]
            }
        },
        {
            "name": "gemini_challenge",
            "description": "Critical thinking tool - challenges ideas, plans, or code to find flaws, risks, and better alternatives. Use this before implementing to catch issues early. Does NOT agree with the user - actively looks for problems.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "statement": {
                        "type": "string",
                        "description": "The idea, plan, architecture, or code to critique. Be specific about what you want challenged."
                    },
                    "context": {
                        "type": "string",
                        "description": "Optional background context, constraints, or requirements that should be considered.",
                        "default": ""
                    },
                    "focus": {
                        "type": "string",
                        "enum": ["general", "security", "performance", "maintainability", "scalability", "cost"],
                        "description": "Specific area to focus the critique on",
                        "default": "general"
                    }
                },
                "required": ["statement"]
            }
        },
        {
            "name": "gemini_generate_code",
            "description": "Generate code using Gemini. Returns structured output with file operations (create/modify) that can be applied by Claude. Best for UI components, boilerplate, and tasks where Gemini excels. Supports @file references for context.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "What code to generate. Be specific about requirements, framework, and style. Example: 'Create a React login component with email/password validation using Tailwind CSS'"
                    },
                    "context_files": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Files to include as context. Supports @file syntax: ['@src/App.tsx', '@package.json', '@src/styles/*.css']. Gemini will match the existing code style."
                    },
                    "language": {
                        "type": "string",
                        "enum": ["auto", "typescript", "javascript", "python", "rust", "go", "java", "cpp", "csharp", "html", "css", "sql"],
                        "description": "Target language. 'auto' detects from context files or prompt.",
                        "default": "auto"
                    },
                    "style": {
                        "type": "string",
                        "enum": ["production", "prototype", "minimal"],
                        "description": "Code style: 'production' (full error handling, types, docs), 'prototype' (working but basic), 'minimal' (bare essentials)",
                        "default": "production"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Best quality code. flash: Faster for simple tasks.",
                        "default": "pro"
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Optional directory to save generated files. If specified, files are saved automatically and a summary is returned. If not specified, returns XML for Claude to apply manually."
                    }
                },
                "required": ["prompt"]
            }
        }
    ]

    # Filter out disabled tools (v2.1.0)
    if DISABLED_TOOLS:
        all_tools = [t for t in all_tools if t["name"] not in DISABLED_TOOLS]

    return all_tools


def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """List available tools"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"tools": get_tools_list()}
    }


# ============ Tool Implementations ============

def tool_ask_gemini(prompt: str, model: str = "pro", temperature: float = 0.5,
                    thinking_level: str = "off", include_thoughts: bool = False,
                    continuation_id: str = None) -> str:
    """
    Gemini query with model selection, thinking capabilities, and conversation memory.

    Thinking allows the model to engage in deeper reasoning for complex tasks.
    - For Gemini 3 Pro: uses thinking_level ("low" or "high")
    - For Gemini 2.5: uses thinking_budget (auto-calculated based on level)

    Supports @file references in prompts to include file contents:
    - @file.py - Include single file
    - @src/main.py - Path with directories
    - @*.py - Glob patterns
    - @src/**/*.ts - Recursive glob patterns

    Supports multi-turn conversations via continuation_id:
    - Omit continuation_id to start a new conversation
    - Pass continuation_id to continue a previous conversation
    - Response includes continuation_id for subsequent calls
    """
    # Expand @file references in prompt
    original_prompt = prompt
    prompt = expand_file_references(prompt)

    # v2.1.0: Check prompt size after file expansion
    size_error = check_prompt_size(prompt)
    if size_error:
        return f"**Error**: {size_error['message']}"

    # Extract file references from expanded prompt for tracking
    files_referenced = []
    if '@' in original_prompt:
        import re
        file_refs = re.findall(r'(?<![a-zA-Z0-9])@([^\s@]+)', original_prompt)
        files_referenced = [ref for ref in file_refs if not '@' in ref]  # Exclude emails

    # Handle conversation memory
    thread_id, is_new, thread = conversation_memory.get_or_create_thread(
        continuation_id=continuation_id,
        metadata={"tool": "ask_gemini", "model": model}
    )

    # Build conversation context if continuing
    conversation_context = ""
    if not is_new and thread:
        conversation_context = thread.build_context()

    # Add user turn to thread
    conversation_memory.add_turn(
        thread_id=thread_id,
        role="user",
        content=original_prompt,
        tool_name="ask_gemini",
        files=files_referenced
    )

    # Combine context with current prompt
    if conversation_context:
        full_prompt = f"{conversation_context}\n\n=== NEW REQUEST ===\n{prompt}"
    else:
        full_prompt = prompt

    model_id = MODELS.get(model, MODELS["pro"])

    # Build config
    config_params = {
        "temperature": temperature,
        "max_output_tokens": 8192
    }

    # Add thinking config if enabled
    if thinking_level != "off":
        thinking_params = {}

        # Include thought summaries if requested
        if include_thoughts:
            thinking_params["include_thoughts"] = True

        # For Gemini 3 Pro, use thinking_level
        if model == "pro":
            thinking_params["thinking_level"] = thinking_level
        else:
            # For Gemini 2.5 models, use thinking_budget
            # Map levels to budgets: low=1024, high=8192
            budget_map = {"low": 1024, "high": 8192}
            thinking_params["thinking_budget"] = budget_map.get(thinking_level, 1024)

        config_params["thinking_config"] = types.ThinkingConfig(**thinking_params)

    response = generate_with_fallback(
        model_id=model_id,
        contents=full_prompt,
        config=types.GenerateContentConfig(**config_params),
        operation="ask_gemini"
    )

    # Extract response text
    response_text = ""
    if include_thoughts and thinking_level != "off":
        result_parts = []
        thoughts_parts = []
        answer_parts = []

        for part in response.candidates[0].content.parts:
            if not hasattr(part, 'text') or not part.text:
                continue
            if hasattr(part, 'thought') and part.thought:
                thoughts_parts.append(part.text)
            else:
                answer_parts.append(part.text)

        if thoughts_parts:
            result_parts.append("**Thought Summary:**\n" + "\n".join(thoughts_parts))
        if answer_parts:
            result_parts.append("**Answer:**\n" + "\n".join(answer_parts))

        # Add token usage info
        if hasattr(response, 'usage_metadata'):
            meta = response.usage_metadata
            if hasattr(meta, 'thoughts_token_count'):
                result_parts.append(f"\n*Thinking tokens: {meta.thoughts_token_count}*")

        response_text = "\n\n".join(result_parts) if result_parts else response.text
    else:
        response_text = response.text

    # Add assistant turn to thread
    conversation_memory.add_turn(
        thread_id=thread_id,
        role="assistant",
        content=response_text,
        tool_name="ask_gemini",
        files=[]
    )

    # Format output with continuation_id
    output = f"**GEMINI (ask_gemini):**\n\n{response_text}"

    # Add continuation info
    thread = conversation_memory.get_thread(thread_id)
    turn_count = len(thread.turns) if thread else 0
    output += f"\n\n---\n*continuation_id: {thread_id}* (turn {turn_count}/{CONVERSATION_MAX_TURNS})"

    return output


def tool_code_review(code: str, focus: str = "general", model: str = "pro") -> str:
    """
    Code review with specific focus.

    Supports @file references in code parameter to include file contents:
    - @src/main.py - Review a specific file
    - @*.py - Review multiple files matching pattern
    """
    # Expand @file references in code
    code = expand_file_references(code)

    # v2.1.0: Check prompt size after file expansion
    size_error = check_prompt_size(code)
    if size_error:
        return f"**Error**: {size_error['message']}"

    prompt = f"""Review this code with focus on {focus}:

```
{code}
```

Provide specific, actionable feedback on:
1. Potential issues or bugs
2. Security concerns
3. Performance optimizations
4. Best practices
5. Code clarity"""

    return tool_ask_gemini(prompt, model=model, temperature=0.2)


def get_methodology_instructions(methodology: str, domain: str = None) -> str:
    """Get methodology-specific instructions for structured brainstorming"""
    methodologies = {
        "divergent": """**Divergent Thinking Approach:**
- Generate maximum quantity of ideas without self-censoring
- Build on wild or seemingly impractical ideas
- Combine unrelated concepts for unexpected solutions
- Use "Yes, and..." thinking to expand each concept
- Postpone evaluation until all ideas are generated""",

        "convergent": """**Convergent Thinking Approach:**
- Focus on refining and improving existing concepts
- Synthesize related ideas into stronger solutions
- Apply critical evaluation criteria
- Prioritize based on feasibility and impact
- Develop implementation pathways for top ideas""",

        "scamper": """**SCAMPER Creative Triggers:**
- **Substitute:** What can be substituted or replaced?
- **Combine:** What can be combined or merged?
- **Adapt:** What can be adapted from other domains?
- **Modify:** What can be magnified, minimized, or altered?
- **Put to other use:** How else can this be used?
- **Eliminate:** What can be removed or simplified?
- **Reverse:** What can be rearranged or reversed?""",

        "design-thinking": """**Human-Centered Design Thinking:**
- **Empathize:** Consider user needs, pain points, and contexts
- **Define:** Frame problems from user perspective
- **Ideate:** Generate user-focused solutions
- **Consider Journey:** Think through complete user experience
- **Prototype Mindset:** Focus on testable, iterative concepts""",

        "lateral": """**Lateral Thinking Approach:**
- Make unexpected connections between unrelated fields
- Challenge fundamental assumptions
- Use random word association to trigger new directions
- Apply metaphors and analogies from other domains
- Reverse conventional thinking patterns""",

        "auto": f"""**AI-Optimized Approach:**
{f'Given the {domain} domain, I will apply the most effective combination of:' if domain else 'I will intelligently combine multiple methodologies:'}
- Divergent exploration with domain-specific knowledge
- SCAMPER triggers and lateral thinking
- Human-centered perspective for practical value"""
    }
    return methodologies.get(methodology, methodologies["auto"])


def tool_brainstorm(topic: str, context: str = "", methodology: str = "auto",
                    domain: str = None, constraints: str = None,
                    idea_count: int = 10, include_analysis: bool = True) -> str:
    """
    Advanced brainstorming with multiple methodologies.

    Methodologies:
    - auto: AI selects best approach
    - divergent: Generate many ideas without filtering
    - convergent: Refine and improve existing concepts
    - scamper: Systematic creative triggers (Substitute, Combine, Adapt, Modify, Put to other use, Eliminate, Reverse)
    - design-thinking: Human-centered approach
    - lateral: Unexpected connections and assumption challenges

    Supports @file references in topic and context to include file contents.
    """
    # Expand @file references in topic and context
    topic = expand_file_references(topic)
    if context:
        context = expand_file_references(context)

    # v2.1.0: Check combined prompt size after file expansion
    combined = topic + (context or "")
    size_error = check_prompt_size(combined)
    if size_error:
        return f"**Error**: {size_error['message']}"

    framework = get_methodology_instructions(methodology, domain)

    prompt = f"""# BRAINSTORMING SESSION

## Core Challenge
{topic}

## Methodology Framework
{framework}

## Context Engineering
*Use the following context to inform your reasoning:*
{f'**Domain Focus:** {domain} - Apply domain-specific knowledge, terminology, and best practices.' if domain else ''}
{f'**Constraints & Boundaries:** {constraints}' if constraints else ''}
{f'**Background Context:** {context}' if context else ''}

## Output Requirements
- Generate {idea_count} distinct, creative ideas
- Each idea should be unique and non-obvious
- Focus on actionable, implementable concepts
- Use clear, descriptive naming
- Provide brief explanations for each idea
"""

    if include_analysis:
        prompt += """
## Analysis Framework
For each idea, provide:
- **Feasibility:** Implementation difficulty (1-5 scale)
- **Impact:** Potential value/benefit (1-5 scale)
- **Innovation:** Uniqueness/creativity (1-5 scale)
- **Quick Assessment:** One-sentence evaluation
"""

    prompt += """
## Format
Present ideas in a structured format:

### Idea [N]: [Creative Name]
**Description:** [2-3 sentence explanation]
"""

    if include_analysis:
        prompt += """**Feasibility:** [1-5] | **Impact:** [1-5] | **Innovation:** [1-5]
**Assessment:** [Brief evaluation]
"""

    prompt += """
---

**Before finalizing, review the list: remove near-duplicates and ensure each idea satisfies the constraints.**

Begin brainstorming session:"""

    return tool_ask_gemini(prompt, model="pro", temperature=0.7)


def tool_web_search(query: str, model: str = "flash") -> str:
    """Web search with Google grounding"""
    model_id = MODELS.get(model, MODELS["flash"])

    response = generate_with_fallback(
        model_id=model_id,
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3
        ),
        operation="web_search"
    )

    result = response.text

    # Extract grounding metadata if available
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                result += "\n\n**Sources:**\n"
                for chunk in metadata.grounding_chunks[:5]:
                    if hasattr(chunk, 'web') and chunk.web:
                        result += f"- [{chunk.web.title}]({chunk.web.uri})\n"

    return result


def tool_create_file_store(name: str) -> str:
    """Create a File Search Store"""
    store = client.file_search_stores.create(
        config={"display_name": name}
    )
    return f"Created File Search Store:\n- Name: {store.name}\n- Display Name: {name}\n\nUse this store_name for uploads and queries: {store.name}"


def tool_upload_file(file_path: str, store_name: str) -> str:
    """Upload file to File Search Store"""
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    log_progress(f"📤 Uploading '{filename}' ({file_size / 1024:.1f} KB) to RAG store...")

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        config={"display_name": filename}
    )

    # Wait for completion (with timeout)
    timeout = 120
    start = time.time()
    while not operation.done and (time.time() - start) < timeout:
        time.sleep(2)
        operation = client.operations.get(operation)

    if operation.done:
        log_progress(f"✅ Upload completed: '{filename}'")
        return f"Successfully uploaded '{filename}' to store {store_name}"
    else:
        log_progress(f"⏳ Upload still in progress: '{filename}'")
        return f"Upload in progress for '{filename}'. Check back later."


def tool_file_search(question: str, store_name: str) -> str:
    """Query documents using File Search RAG"""
    response = generate_with_fallback(
        model_id="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )
            ]
        ),
        operation="file_search"
    )

    result = response.text

    # Add citations if available
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                result += "\n\n**Citations:**\n"
                for i, chunk in enumerate(metadata.grounding_chunks[:5], 1):
                    if hasattr(chunk, 'retrieved_context'):
                        ctx = chunk.retrieved_context
                        result += f"{i}. {ctx.title if hasattr(ctx, 'title') else 'Document'}\n"

    return result


def tool_list_file_stores() -> str:
    """List all File Search Stores"""
    stores = client.file_search_stores.list()
    if not stores:
        return "No File Search Stores found. Create one with gemini_create_file_store."

    result = "**Available File Search Stores:**\n"
    for store in stores:
        result += f"- {store.display_name}: `{store.name}`\n"
    return result


def tool_analyze_image(image_path: str, prompt: str = "Describe this image in detail",
                       model: str = "flash") -> str:
    """
    Analyze an image using Gemini vision capabilities.

    Supports: PNG, JPG, JPEG, GIF, WEBP
    Use cases: describe images, extract text (OCR), identify objects, answer questions
    """
    try:
        if not os.path.exists(image_path):
            return f"Error: Image not found: {image_path}"

        # Determine MIME type
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }

        mime_type = mime_types.get(ext)
        if not mime_type:
            return f"Error: Unsupported image format: {ext}. Supported: PNG, JPG, JPEG, GIF, WEBP"

        # Read image and encode to base64
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Select model
        model_id = MODELS.get(model, MODELS["pro"])

        # Create image part
        image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)

        # Generate response
        response = generate_with_fallback(
            model_id=model_id,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096
            ),
            operation="analyze_image"
        )

        return response.text

    except Exception as e:
        return f"Image analysis error: {str(e)}"


def tool_generate_image(prompt: str, model: str = "pro", aspect_ratio: str = "1:1",
                        image_size: str = "2K", output_path: str = None) -> str:
    """
    Generate image using Gemini native image generation.
    Defaults to Gemini 3 Pro for best quality.

    Models:
    - pro: gemini-3-pro-image-preview (high quality, up to 4K, thinking mode) - DEFAULT
    - flash: gemini-2.5-flash-image (fast, 1024px max)

    Best practices:
    - Use descriptive prompts, not keyword lists
    - Specify style, lighting, camera angle, mood
    - For photorealism: mention lens type, lighting setup
    - For illustrations: specify art style, line style, colors
    """
    try:
        # Select model - default to Pro for best quality
        model_id = IMAGE_MODELS.get(model, IMAGE_MODELS["pro"])

        # Build config
        config_params = {
            "response_modalities": ["IMAGE", "TEXT"]
        }

        # Add image config for aspect ratio and size
        image_config = {"aspect_ratio": aspect_ratio}

        # image_size only supported by pro model
        if model == "pro" and image_size in ["1K", "2K", "4K"]:
            image_config["image_size"] = image_size

        config_params["image_config"] = types.ImageConfig(**image_config)

        log_progress(f"🎨 Generating {image_size} image with {model_id}...")

        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(**config_params)
        )

        log_progress("✅ Image generation completed")

        # Look for image in response parts
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type

                # Determine file extension
                ext = ".png"
                if "jpeg" in mime_type:
                    ext = ".jpg"
                elif "webp" in mime_type:
                    ext = ".webp"

                if output_path:
                    # Ensure correct extension
                    if not output_path.endswith(ext):
                        output_path = output_path.rsplit('.', 1)[0] + ext
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    return f"Image saved to: {output_path}\nModel: {model_id}\nAspect ratio: {aspect_ratio}"
                else:
                    b64 = base64.b64encode(image_data).decode('utf-8')
                    return f"Generated image ({mime_type})\nModel: {model_id}\nAspect ratio: {aspect_ratio}\nBase64 (first 100 chars): {b64[:100]}...\nTotal size: {len(b64)} characters"

        # If no image found, return text response if any
        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
        if text_parts:
            return f"No image generated. Model response: {' '.join(text_parts)}"
        return "No image generated. Try a more descriptive prompt."

    except Exception as e:
        return f"Image generation error: {str(e)}"


def tool_generate_video(prompt: str, model: str = "veo31", aspect_ratio: str = "16:9",
                        duration: int = 8, resolution: str = "720p",
                        negative_prompt: str = None, output_path: str = None) -> str:
    """
    Generate video using Google Veo 3.1 - state-of-the-art video generation with native audio.

    Models:
    - veo31: Best quality, 720p/1080p, 4-8 seconds, native audio (DEFAULT)
    - veo31_fast: Faster generation, optimized for speed
    - veo3: Stable version with audio
    - veo3_fast: Fast stable version
    - veo2: Legacy, no audio

    Best practices for prompts:
    - Include: subject, action, style, camera motion, composition, ambiance
    - For dialogue: use quotes ("Hello," she said)
    - For sound effects: describe explicitly (tires screeching, engine roaring)
    - For ambient noise: describe environment's soundscape
    """
    try:
        model_id = VIDEO_MODELS.get(model, VIDEO_MODELS["veo31"])

        # Build config
        config_params = {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": str(duration),
        }

        # Resolution only for Veo 3.1 (1080p requires 8s duration)
        if model in ["veo31", "veo31_fast"]:
            if resolution == "1080p" and duration != 8:
                config_params["resolution"] = "720p"  # 1080p requires 8s
            else:
                config_params["resolution"] = resolution

        # Add negative prompt if provided
        if negative_prompt:
            config_params["negative_prompt"] = negative_prompt

        # Person generation - required for Veo
        config_params["person_generation"] = "allow_all"

        log_progress(f"🎬 Starting video generation with {model_id} ({duration}s, {resolution})...")
        log_progress("⏳ This may take 1-6 minutes...")

        # Start video generation
        operation = client.models.generate_videos(
            model=model_id,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_params)
        )

        # Poll for completion (video generation can take 1-6 minutes)
        max_wait = 360  # 6 minutes max
        poll_interval = 10
        elapsed = 0

        while not operation.done and elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            log_progress(f"⏳ Video generation in progress... ({elapsed}s elapsed)")
            operation = client.operations.get(operation)

        if not operation.done:
            log_progress("❌ Video generation timed out")
            return f"Video generation timed out after {max_wait} seconds. Operation may still be running."

        log_progress("✅ Video generation completed")

        # Check for errors
        if hasattr(operation, 'error') and operation.error:
            return f"Video generation failed: {operation.error}"

        # Get generated video
        if not hasattr(operation, 'response') or not operation.response:
            return "Video generation completed but no response received."

        generated_videos = operation.response.generated_videos
        if not generated_videos:
            return "No video was generated. Try a different prompt."

        video = generated_videos[0]

        # Download the video
        client.files.download(file=video.video)

        if output_path:
            # Ensure .mp4 extension
            if not output_path.endswith('.mp4'):
                output_path = output_path.rsplit('.', 1)[0] + '.mp4' if '.' in output_path else output_path + '.mp4'

            video.video.save(output_path)

            return f"""Video generated successfully!
- Saved to: {output_path}
- Model: {model_id}
- Duration: {duration}s
- Resolution: {resolution}
- Aspect ratio: {aspect_ratio}
- Has audio: {'Yes' if model != 'veo2' else 'No'}"""
        else:
            # Save to temp location and return info
            temp_path = f"/tmp/gemini_video_{int(time.time())}.mp4"
            video.video.save(temp_path)

            return f"""Video generated successfully!
- Temporary file: {temp_path}
- Model: {model_id}
- Duration: {duration}s
- Resolution: {resolution}
- Aspect ratio: {aspect_ratio}
- Has audio: {'Yes' if model != 'veo2' else 'No'}

Note: Specify output_path to save to a custom location."""

    except Exception as e:
        return f"Video generation error: {str(e)}"


def tool_text_to_speech(text: str, voice: str = "Kore", model: str = "flash",
                        speakers: List[Dict[str, str]] = None,
                        output_path: str = None) -> str:
    """
    Generate speech from text using Gemini TTS.
    Supports single-speaker and multi-speaker (up to 2) audio generation.

    Models:
    - flash: Fast TTS generation (default)
    - pro: Higher quality TTS

    Voices (30 options): Zephyr (Bright), Puck (Upbeat), Charon (Informative),
    Kore (Firm), Fenrir (Excitable), Leda (Youthful), and more.

    For multi-speaker, use the speakers parameter with format:
    [{"name": "Speaker1", "voice": "Kore"}, {"name": "Speaker2", "voice": "Puck"}]

    Style control: Include style instructions in the text prompt, e.g.,
    "Say cheerfully: Hello!" or "Speaker1 sounds tired, Speaker2 sounds excited"
    """
    try:
        model_id = TTS_MODELS.get(model, TTS_MODELS["flash"])

        # Build speech config
        if speakers and len(speakers) >= 2:
            # Multi-speaker mode
            speaker_configs = []
            for speaker in speakers[:2]:  # Max 2 speakers
                speaker_name = speaker.get("name", "Speaker")
                speaker_voice = speaker.get("voice", "Kore")
                # Validate voice
                if speaker_voice not in TTS_VOICES:
                    speaker_voice = "Kore"

                speaker_configs.append(
                    types.SpeakerVoiceConfig(
                        speaker=speaker_name,
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=speaker_voice
                            )
                        )
                    )
                )

            speech_config = types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_configs
                )
            )
        else:
            # Single-speaker mode
            if voice not in TTS_VOICES:
                voice = "Kore"

            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            )

        # Generate audio
        response = client.models.generate_content(
            model=model_id,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config
            )
        )

        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Determine output path
        if not output_path:
            output_path = f"/tmp/gemini_tts_{int(time.time())}.wav"
        elif not output_path.endswith('.wav'):
            output_path = output_path.rsplit('.', 1)[0] + '.wav' if '.' in output_path else output_path + '.wav'

        # Save as WAV file (PCM 24kHz, 16-bit, mono)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit
            wf.setframerate(24000)    # 24kHz
            wf.writeframes(audio_data)

        # Calculate duration
        duration_sec = len(audio_data) / (24000 * 2)  # samples / (rate * bytes_per_sample)

        mode = "Multi-speaker" if (speakers and len(speakers) >= 2) else "Single-speaker"
        voice_info = ", ".join([f"{s['name']}: {s['voice']}" for s in speakers[:2]]) if speakers else voice

        return f"""Audio generated successfully!
- Saved to: {output_path}
- Model: {model_id}
- Mode: {mode}
- Voice(s): {voice_info}
- Duration: {duration_sec:.1f}s
- Format: WAV (24kHz, 16-bit, mono)"""

    except Exception as e:
        return f"TTS generation error: {str(e)}"


def tool_analyze_codebase(prompt: str, files: List[str], analysis_type: str = "general",
                          model: str = "pro", continuation_id: str = None) -> str:
    """
    Analyze large codebases using Gemini's 1M token context window.

    Leverages Gemini's massive context to analyze entire codebases at once,
    something Claude's smaller context can't easily do.

    Args:
        prompt: The analysis task or question
        files: List of file paths (supports glob patterns)
        analysis_type: Focus area (architecture, security, refactoring, etc.)
        model: Gemini model to use
        continuation_id: For iterative analysis with memory
    """
    import glob as glob_module

    # Expand glob patterns and collect files
    all_files = []
    for pattern in files:
        # Handle glob patterns
        if '*' in pattern or '?' in pattern:
            expanded = glob_module.glob(pattern, recursive=True)
            all_files.extend([f for f in expanded if os.path.isfile(f)])
        elif os.path.isfile(pattern):
            all_files.append(pattern)
        elif os.path.isdir(pattern):
            # If directory, get all files recursively
            for root, dirs, filenames in os.walk(pattern):
                for filename in filenames:
                    all_files.append(os.path.join(root, filename))

    # Remove duplicates while preserving order
    seen = set()
    unique_files = []
    for f in all_files:
        if f not in seen:
            seen.add(f)
            unique_files.append(f)
    all_files = unique_files

    if not all_files:
        return "**Error**: No files found matching the provided patterns."

    # Read file contents
    file_contents = []
    total_chars = 0
    skipped_files = []
    max_file_size = 100_000  # 100KB per file max

    for filepath in all_files:
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()

            # Skip very large files
            if len(content) > max_file_size:
                skipped_files.append(f"{filepath} (too large: {len(content):,} chars)")
                continue

            # Skip binary files
            if '\x00' in content[:1000]:
                skipped_files.append(f"{filepath} (binary file)")
                continue

            file_contents.append({
                "path": filepath,
                "content": content,
                "size": len(content)
            })
            total_chars += len(content)

        except Exception as e:
            skipped_files.append(f"{filepath} (error: {str(e)})")

    if not file_contents:
        return "**Error**: Could not read any files. Check paths and permissions."

    # Estimate tokens
    estimated_tokens = estimate_tokens(str(total_chars))

    # Build analysis prompt based on type
    analysis_instructions = {
        "architecture": """Focus on:
- Overall project structure and organization
- Design patterns used
- Component relationships and dependencies
- Entry points and data flow
- Architectural strengths and weaknesses""",
        "security": """Focus on:
- Potential security vulnerabilities (OWASP Top 10)
- Input validation and sanitization
- Authentication and authorization patterns
- Sensitive data handling
- Injection risks (SQL, command, XSS)""",
        "refactoring": """Focus on:
- Code duplication and DRY violations
- Long methods or classes that should be split
- Poor naming or unclear abstractions
- Tight coupling between components
- Opportunities for design pattern application""",
        "documentation": """Focus on:
- Missing or outdated documentation
- Functions/classes without docstrings
- Complex logic without explanatory comments
- API documentation completeness
- README and setup instructions""",
        "dependencies": """Focus on:
- External library usage and versions
- Circular dependencies
- Unused imports or dependencies
- Dependency injection patterns
- Package organization""",
        "general": """Provide a comprehensive analysis covering:
- Architecture and structure
- Code quality and maintainability
- Potential issues or risks
- Recommendations for improvement"""
    }

    instructions = analysis_instructions.get(analysis_type, analysis_instructions["general"])

    # Build the codebase content
    codebase_content = []
    for fc in file_contents:
        ext = os.path.splitext(fc["path"])[1].lstrip('.')
        codebase_content.append(f"### FILE: {fc['path']}\n```{ext}\n{fc['content']}\n```\n")

    codebase_text = "\n".join(codebase_content)

    # Handle conversation memory
    thread_id, is_new, thread = conversation_memory.get_or_create_thread(
        continuation_id=continuation_id,
        metadata={"tool": "analyze_codebase", "model": model, "analysis_type": analysis_type}
    )

    # Build conversation context if continuing
    conversation_context = ""
    if not is_new and thread:
        conversation_context = thread.build_context(max_tokens=200000)  # Reserve space for code

    # Add user turn
    files_list = [fc["path"] for fc in file_contents]
    conversation_memory.add_turn(thread_id, "user", prompt, "analyze_codebase", files_list)

    # Build full prompt
    full_prompt = f"""# CODEBASE ANALYSIS REQUEST

## Analysis Type: {analysis_type.upper()}

{instructions}

## User Request
{prompt}

## Codebase Statistics
- Files analyzed: {len(file_contents)}
- Total size: {total_chars:,} characters (~{estimated_tokens:,} tokens)
{f"- Skipped files: {len(skipped_files)}" if skipped_files else ""}

## Codebase Contents

{codebase_text}

---
Provide a thorough analysis based on the above codebase and the user's request.
Structure your response clearly with sections and specific file references where applicable."""

    if conversation_context:
        full_prompt = f"{conversation_context}\n\n=== NEW ANALYSIS REQUEST ===\n{full_prompt}"

    # Check prompt size (use higher limit since Gemini has 1M context)
    if len(full_prompt) > 3_000_000:  # ~750K tokens, leave room for response
        return f"**Error**: Combined codebase too large ({len(full_prompt):,} chars). Try analyzing fewer files or specific directories."

    try:
        model_id = MODELS.get(model, MODELS["pro"])

        response = client.models.generate_content(
            model=model_id,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for analysis
                max_output_tokens=8192
            )
        )

        if not response.candidates:
            return "No response generated. The codebase may have been blocked by safety filters."

        result_text = response.text

        # Add assistant turn
        conversation_memory.add_turn(thread_id, "assistant", result_text, "analyze_codebase", [])
        turn_count = len(thread.turns) if thread else 2

        # Build output
        output = f"""## Codebase Analysis Results

**Files Analyzed:** {len(file_contents)} ({total_chars:,} chars)
**Model:** {model_id}
**Analysis Type:** {analysis_type}
{f"**Skipped:** {len(skipped_files)} files" if skipped_files else ""}

---

{result_text}

---
*continuation_id: {thread_id}* (turn {turn_count}/{CONVERSATION_MAX_TURNS})
*Use continuation_id for follow-up questions about this codebase*"""

        return output

    except Exception as e:
        error_msg = str(e)
        if "quota" in error_msg.lower() or "429" in error_msg:
            # Try with flash model
            try:
                response = client.models.generate_content(
                    model=MODELS["flash"],
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=8192
                    )
                )
                result_text = response.text
                conversation_memory.add_turn(thread_id, "assistant", result_text, "analyze_codebase", [])
                turn_count = len(thread.turns) if thread else 2

                return f"""## Codebase Analysis Results (Flash Fallback)

**Files Analyzed:** {len(file_contents)} ({total_chars:,} chars)
**Model:** {MODELS["flash"]} (fallback due to quota)
**Analysis Type:** {analysis_type}

---

{result_text}

---
*continuation_id: {thread_id}* (turn {turn_count}/{CONVERSATION_MAX_TURNS})"""
            except:
                pass
        return f"Analysis error: {error_msg}"


def tool_challenge(statement: str, context: str = "", focus: str = "general") -> str:
    """
    Critical thinking tool - challenges ideas, plans, or code to find flaws.

    Acts as a "Devil's Advocate" to:
    - Find potential problems before implementation
    - Identify risks and edge cases
    - Suggest better alternatives
    - Challenge assumptions

    Does NOT agree with the user - actively looks for problems.
    """
    # Expand @file references
    statement = expand_file_references(statement)
    if context:
        context = expand_file_references(context)

    # Check prompt size
    combined = statement + (context or "")
    size_error = check_prompt_size(combined)
    if size_error:
        return f"**Error**: {size_error['message']}"

    # Focus-specific instructions
    focus_instructions = {
        "security": """**Security Focus:**
- Identify potential vulnerabilities (OWASP Top 10)
- Find authentication/authorization gaps
- Look for injection risks (SQL, command, XSS)
- Check for data exposure risks
- Evaluate cryptographic weaknesses""",

        "performance": """**Performance Focus:**
- Identify bottlenecks and inefficiencies
- Find N+1 query problems or expensive operations
- Look for memory leaks or resource issues
- Check for scalability concerns
- Evaluate caching opportunities missed""",

        "maintainability": """**Maintainability Focus:**
- Find overly complex or unclear code/design
- Identify tight coupling and poor abstractions
- Look for violation of SOLID principles
- Check for testing difficulties
- Evaluate documentation gaps""",

        "scalability": """**Scalability Focus:**
- Identify single points of failure
- Find state management issues
- Look for horizontal scaling blockers
- Check for database/storage bottlenecks
- Evaluate load distribution concerns""",

        "cost": """**Cost Focus:**
- Identify expensive operations or resources
- Find inefficient resource utilization
- Look for hidden costs (API calls, storage, compute)
- Check for cost scaling concerns
- Evaluate cheaper alternatives""",

        "general": """**General Critical Analysis:**
- Find logical flaws and inconsistencies
- Identify hidden assumptions
- Look for edge cases and failure modes
- Check for missing requirements
- Evaluate alternative approaches"""
    }

    focus_instruction = focus_instructions.get(focus, focus_instructions["general"])

    prompt = f"""# CRITICAL ANALYSIS REQUEST

## Your Role
You are a critical thinker and "Devil's Advocate". Your job is to find problems, risks, and flaws.

**IMPORTANT INSTRUCTIONS:**
- Do NOT agree with or validate the idea
- Do NOT be encouraging or positive
- Do NOT soften your critique
- Be direct, honest, and thorough
- Find REAL problems, not hypothetical nitpicks
- Prioritize by severity

{focus_instruction}

## Statement to Challenge
{statement}

{f'## Additional Context\n{context}' if context else ''}

## Required Output Structure

### 1. Critical Flaws (Must Fix)
List the most serious problems that would cause failure if not addressed.

### 2. Significant Risks
Problems that may not be immediately fatal but pose real danger.

### 3. Questionable Assumptions
Assumptions made that may not hold true.

### 4. Missing Considerations
Important aspects not addressed in the proposal.

### 5. Better Alternatives
Different approaches that might work better, with brief rationale.

### 6. Devil's Advocate Summary
A 2-3 sentence harsh but fair summary of why this might fail.

---
Be thorough but actionable. Focus on the most impactful issues first.
"""

    return tool_ask_gemini(prompt, model="pro", temperature=0.4)


def parse_generated_code(xml_content: str) -> List[Dict[str, str]]:
    """
    Parse <FILE> blocks from generated code XML.

    Returns list of dicts with keys: action, path, content
    Example: [{"action": "create", "path": "src/app.py", "content": "..."}]
    """
    import re
    files = []

    # Find all <FILE ...>...</FILE> blocks
    pattern = r'<FILE\s+action=["\']([^"\']+)["\']\s+path=["\']([^"\']+)["\']>\s*(.*?)\s*</FILE>'
    matches = re.findall(pattern, xml_content, re.DOTALL)

    for action, path, content in matches:
        # Clean up content - remove leading/trailing whitespace but preserve internal structure
        content = content.strip()
        files.append({
            "action": action,
            "path": path,
            "content": content
        })

    return files


def save_generated_files(files: List[Dict[str, str]], output_dir: str) -> List[Dict[str, Any]]:
    """
    Save parsed files to disk.

    Returns list of results with status for each file.
    """
    results = []

    for file_info in files:
        action = file_info["action"]
        rel_path = file_info["path"]
        content = file_info["content"]

        try:
            # Construct full path
            full_path = os.path.join(output_dir, rel_path)

            # Validate path is within sandbox
            validated_path = validate_path(full_path)

            # Create directories if needed
            dir_path = os.path.dirname(validated_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

            # Write file
            with open(validated_path, 'w', encoding='utf-8') as f:
                f.write(content)

            results.append({
                "path": rel_path,
                "full_path": validated_path,
                "action": action,
                "status": "success",
                "lines": len(content.split('\n'))
            })

        except PermissionError as e:
            results.append({
                "path": rel_path,
                "action": action,
                "status": "error",
                "error": f"Permission denied: {str(e)}"
            })
        except Exception as e:
            results.append({
                "path": rel_path,
                "action": action,
                "status": "error",
                "error": str(e)
            })

    return results


def tool_generate_code(prompt: str, context_files: List[str] = None,
                       language: str = "auto", style: str = "production",
                       model: str = "pro", output_dir: str = None) -> str:
    """
    Generate code using Gemini with structured output for Claude to apply.

    Returns XML-formatted output with file operations:
    - <FILE action="create" path="...">: New file to create
    - <FILE action="modify" path="...">: Existing file to modify

    Claude can parse this output and apply the changes.
    """
    # Build context from files
    context_content = ""
    if context_files:
        context_parts = []
        for file_ref in context_files:
            # Ensure @ prefix for expand_file_references
            if not file_ref.startswith('@'):
                file_ref = '@' + file_ref
            expanded = expand_file_references(file_ref)
            if expanded != file_ref:  # File was found and expanded
                context_parts.append(expanded)
        if context_parts:
            context_content = "\n\n".join(context_parts)

    # Check prompt size
    combined = prompt + context_content
    size_error = check_prompt_size(combined)
    if size_error:
        return f"**Error**: {size_error['message']}"

    # Style-specific instructions
    style_instructions = {
        "production": """**Production Quality Code:**
- Full error handling with informative messages
- Complete type annotations/hints
- JSDoc/docstrings for public APIs
- Input validation where appropriate
- Follow established patterns from context files
- Include necessary imports""",

        "prototype": """**Prototype Quality Code:**
- Working code with basic error handling
- Key type annotations only
- Brief comments for complex logic
- Focus on functionality over polish""",

        "minimal": """**Minimal Code:**
- Bare essentials only
- No comments unless critical
- Minimal error handling
- Shortest working solution"""
    }

    style_instruction = style_instructions.get(style, style_instructions["production"])

    # Language detection hint
    lang_hint = ""
    if language != "auto":
        lang_hint = f"\n**Target Language:** {language}"

    # Build the prompt
    full_prompt = f"""# CODE GENERATION REQUEST

## Task
{prompt}
{lang_hint}

{style_instruction}

## Output Format
You MUST return code in this EXACT XML format. This format allows automated processing.

```xml
<GENERATED_CODE>
<FILE action="create" path="relative/path/to/newfile.ext">
// Complete file contents here
// Include ALL necessary code - imports, types, implementation
</FILE>

<FILE action="modify" path="relative/path/to/existing.ext">
// Show the COMPLETE modified file
// Or use comments to indicate unchanged sections:
// ... existing imports ...

// NEW OR MODIFIED CODE HERE

// ... rest of file unchanged ...
</FILE>
</GENERATED_CODE>
```

## Rules
1. Use action="create" for new files
2. Use action="modify" for changes to existing files
3. Paths should be relative to project root
4. Include complete, runnable code - no placeholders like "// add your code here"
5. Match the code style from context files if provided
6. Each FILE block must contain the full file OR clearly marked sections

## Need More Context?
If you need to see additional files before generating code, respond with ONLY:
```json
{{"need_files": ["path/to/file1.ts", "path/to/file2.py"]}}
```
Do NOT include any other text. I will provide the requested files and ask again.

{f'## Context Files (match this style){chr(10)}{context_content}' if context_content else ''}

## Generate Code Now
Return ONLY the <GENERATED_CODE> block with the requested implementation.
If you need more files first, return ONLY the JSON need_files request.
"""

    model_id = MODELS.get(model, MODELS["pro"])

    try:
        response = generate_with_fallback(
            model_id=model_id,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for consistent code
                max_output_tokens=8192
            ),
            operation="generate_code"
        )

        result = response.text

        # v2.5.0: JSON More Info Protocol - detect need_files requests
        import re
        need_files_match = re.search(r'\{\s*"need_files"\s*:\s*\[(.*?)\]\s*\}', result, re.DOTALL)
        if need_files_match and "<GENERATED_CODE>" not in result:
            # Gemini is requesting more files
            try:
                # Parse the JSON request
                files_str = need_files_match.group(1)
                # Extract file paths from the JSON array
                requested_files = re.findall(r'"([^"]+)"', files_str)

                if requested_files:
                    # Fetch requested files and retry (max 1 retry to prevent loops)
                    additional_context = []
                    for file_path in requested_files[:5]:  # Limit to 5 files
                        file_ref = f"@{file_path}" if not file_path.startswith('@') else file_path
                        expanded = expand_file_references(file_ref)
                        if expanded != file_ref:
                            additional_context.append(expanded)

                    if additional_context:
                        # Add new context and retry
                        new_context = context_content + "\n\n" + "\n\n".join(additional_context)

                        retry_prompt = f"""# CODE GENERATION REQUEST (RETRY WITH ADDITIONAL FILES)

## Task
{prompt}
{lang_hint}

{style_instruction}

## Output Format
You MUST return code in this EXACT XML format:
```xml
<GENERATED_CODE>
<FILE action="create" path="relative/path/to/file.ext">
// Complete file contents
</FILE>
</GENERATED_CODE>
```

## Context Files (match this style)
{new_context}

## Generate Code Now
You now have the additional files you requested. Return ONLY the <GENERATED_CODE> block.
"""
                        retry_response = generate_with_fallback(
                            model_id=model_id,
                            contents=retry_prompt,
                            config=types.GenerateContentConfig(
                                temperature=0.3,
                                max_output_tokens=8192
                            ),
                            operation="generate_code_retry"
                        )
                        result = retry_response.text

            except Exception as e:
                # If retry fails, continue with original result
                pass

        # Validate output format
        if "<GENERATED_CODE>" not in result:
            # Gemini didn't follow format - wrap it
            result = f"""<GENERATED_CODE>
<FILE action="create" path="generated_code.txt">
{result}
</FILE>
</GENERATED_CODE>

**Note:** Gemini didn't return structured output. Review and apply manually."""

        # v2.5.0: Auto-save if output_dir is specified
        if output_dir:
            try:
                # Validate output directory
                validated_dir = validate_path(output_dir)

                # Create output directory if it doesn't exist
                if not os.path.exists(validated_dir):
                    os.makedirs(validated_dir, exist_ok=True)

                # Parse and save files
                files = parse_generated_code(result)
                if not files:
                    return f"""## Code Generation Result

**Style:** {style}
**Language:** {language}
**Model:** {model_id}
**Output Directory:** {output_dir}

**Warning:** No <FILE> blocks found in output. Raw result:

{result}"""

                save_results = save_generated_files(files, validated_dir)

                # Build summary
                success_count = sum(1 for r in save_results if r["status"] == "success")
                error_count = sum(1 for r in save_results if r["status"] == "error")

                summary_lines = [f"## Code Generation Result",
                                 f"",
                                 f"**Style:** {style}",
                                 f"**Language:** {language}",
                                 f"**Model:** {model_id}",
                                 f"**Output Directory:** {validated_dir}",
                                 f"",
                                 f"### Files Saved ({success_count} success, {error_count} errors)",
                                 f""]

                for r in save_results:
                    if r["status"] == "success":
                        summary_lines.append(f"- **{r['action']}** `{r['path']}` ({r['lines']} lines)")
                    else:
                        summary_lines.append(f"- **{r['action']}** `{r['path']}` - ERROR: {r['error']}")

                summary_lines.append("")
                summary_lines.append("---")
                summary_lines.append("Files have been saved. Review them to verify correctness.")

                return "\n".join(summary_lines)

            except PermissionError as e:
                return f"**Error:** Cannot write to output directory: {str(e)}"
            except Exception as e:
                return f"**Error:** Failed to save files: {str(e)}"

        # Default: return XML for Claude to apply
        return f"""## Code Generation Result

**Style:** {style}
**Language:** {language}
**Model:** {model_id}

{result}

---
**Instructions for Claude:** Parse the <GENERATED_CODE> block and apply file operations using Write/Edit tools.
- action="create": Use Write tool to create new file
- action="modify": Use Edit tool to modify existing file"""

    except Exception as e:
        return f"Code generation error: {str(e)}"


def handle_tool_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution with activity logging"""
    tool_name = params.get("name")
    args = params.get("arguments", {})

    # v2.6.0: Validate input with Pydantic schemas
    try:
        args = validate_tool_input(tool_name, args)
    except ValueError as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,  # Invalid params
                "message": str(e)
            }
        }

    # Activity logging: record start time
    start_time = time.time()
    log_activity(tool_name, "start", details={"args_keys": list(args.keys())})

    try:
        if not GEMINI_AVAILABLE:
            result = f"Gemini not available: {GEMINI_ERROR}"
        elif tool_name == "ask_gemini":
            result = tool_ask_gemini(
                args.get("prompt", ""),
                args.get("model", "pro"),
                args.get("temperature", 0.5),
                args.get("thinking_level", "off"),
                args.get("include_thoughts", False),
                args.get("continuation_id")
            )
        elif tool_name == "gemini_code_review":
            result = tool_code_review(
                args.get("code", ""),
                args.get("focus", "general"),
                args.get("model", "pro")
            )
        elif tool_name == "gemini_brainstorm":
            result = tool_brainstorm(
                args.get("topic", ""),
                args.get("context", ""),
                args.get("methodology", "auto"),
                args.get("domain"),
                args.get("constraints"),
                args.get("idea_count", 10),
                args.get("include_analysis", True)
            )
        elif tool_name == "gemini_web_search":
            result = tool_web_search(
                args.get("query", ""),
                args.get("model", "flash")
            )
        elif tool_name == "gemini_create_file_store":
            result = tool_create_file_store(args.get("name", ""))
        elif tool_name == "gemini_upload_file":
            result = tool_upload_file(
                args.get("file_path", ""),
                args.get("store_name", "")
            )
        elif tool_name == "gemini_file_search":
            result = tool_file_search(
                args.get("question", ""),
                args.get("store_name", "")
            )
        elif tool_name == "gemini_list_file_stores":
            result = tool_list_file_stores()
        elif tool_name == "gemini_analyze_image":
            result = tool_analyze_image(
                args.get("image_path", ""),
                args.get("prompt", "Describe this image in detail"),
                args.get("model", "flash")
            )
        elif tool_name == "gemini_generate_image":
            result = tool_generate_image(
                args.get("prompt", ""),
                args.get("model", "pro"),
                args.get("aspect_ratio", "1:1"),
                args.get("image_size", "2K"),
                args.get("output_path")
            )
        elif tool_name == "gemini_generate_video":
            result = tool_generate_video(
                args.get("prompt", ""),
                args.get("model", "veo31"),
                args.get("aspect_ratio", "16:9"),
                args.get("duration", 8),
                args.get("resolution", "720p"),
                args.get("negative_prompt"),
                args.get("output_path")
            )
        elif tool_name == "gemini_text_to_speech":
            result = tool_text_to_speech(
                args.get("text", ""),
                args.get("voice", "Kore"),
                args.get("model", "flash"),
                args.get("speakers"),
                args.get("output_path")
            )
        elif tool_name == "gemini_analyze_codebase":
            result = tool_analyze_codebase(
                args.get("prompt", ""),
                args.get("files", []),
                args.get("analysis_type", "general"),
                args.get("model", "pro"),
                args.get("continuation_id")
            )
        elif tool_name == "gemini_challenge":
            result = tool_challenge(
                args.get("statement", ""),
                args.get("context", ""),
                args.get("focus", "general")
            )
        elif tool_name == "gemini_generate_code":
            result = tool_generate_code(
                args.get("prompt", ""),
                args.get("context_files") or [],  # Handle null from MCP
                args.get("language", "auto"),
                args.get("style", "production"),
                args.get("model", "pro"),
                args.get("output_dir")  # v2.5.0: Auto-save to directory
            )
        elif tool_name == "server_status":
            result = f"Server v{__version__}\nGemini: {'Available' if GEMINI_AVAILABLE else 'Error: ' + GEMINI_ERROR}"
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Activity logging: record success
        duration_ms = (time.time() - start_time) * 1000
        log_activity(tool_name, "success", duration_ms=duration_ms,
                     details={"result_len": len(result) if isinstance(result, str) else 0})

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"**GEMINI ({tool_name}):**\n\n{result}"
                }]
            }
        }
    except Exception as e:
        # Activity logging: record error
        duration_ms = (time.time() - start_time) * 1000
        log_activity(tool_name, "error", duration_ms=duration_ms, error=str(e))

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)}
        }


def main():
    """Main server loop"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})

            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "notifications/initialized":
                continue  # No response needed
            elif method == "tools/list":
                response = handle_tools_list(request_id)
            elif method == "tools/call":
                response = handle_tool_call(request_id, params)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            send_response(response)

        except json.JSONDecodeError:
            continue
        except EOFError:
            break
        except Exception as e:
            if 'request_id' in locals() and request_id:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                })


if __name__ == "__main__":
    main()
