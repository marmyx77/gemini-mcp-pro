"""Core modules: config, security, logging."""

from .config import Config, config
from .logging import StructuredLogger, structured_logger, log_activity, log_progress
from .security import (
    SecretsSanitizer,
    SafeFileWriter,
    validate_path,
    check_file_size,
    secure_read_file,
    secure_write_file,
    secrets_sanitizer,
    is_binary_file,
    file_lock,
    FileLockError,
    RegexTimeoutError,
    regex_timeout,
    BINARY_EXTENSIONS,
)

__all__ = [
    "Config",
    "config",
    "StructuredLogger",
    "structured_logger",
    "log_activity",
    "log_progress",
    "SecretsSanitizer",
    "SafeFileWriter",
    "validate_path",
    "check_file_size",
    "secure_read_file",
    "secure_write_file",
    "secrets_sanitizer",
    "is_binary_file",
    "file_lock",
    "FileLockError",
    "RegexTimeoutError",
    "regex_timeout",
    "BINARY_EXTENSIONS",
]
