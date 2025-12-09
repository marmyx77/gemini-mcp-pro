"""
Backward Compatibility Shim Tests for v3.0.0

Tests that server.py re-exports work for existing code.
"""

import pytest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestServerShimImports:
    """Test that old imports from server.py still work."""

    def test_import_sandbox_root(self):
        """SANDBOX_ROOT is importable."""
        from server import SANDBOX_ROOT
        assert SANDBOX_ROOT is not None
        assert isinstance(SANDBOX_ROOT, str)

    def test_import_sandbox_enabled(self):
        """SANDBOX_ENABLED is importable."""
        from server import SANDBOX_ENABLED
        assert isinstance(SANDBOX_ENABLED, bool)

    def test_import_max_file_size(self):
        """MAX_FILE_SIZE is importable."""
        from server import MAX_FILE_SIZE
        assert isinstance(MAX_FILE_SIZE, int)
        assert MAX_FILE_SIZE > 0


class TestSecurityImports:
    """Test security function imports."""

    def test_import_validate_path(self):
        """validate_path is importable."""
        from server import validate_path
        assert callable(validate_path)

    def test_import_check_file_size(self):
        """check_file_size is importable."""
        from server import check_file_size
        assert callable(check_file_size)

    def test_import_secure_read_file(self):
        """secure_read_file is importable."""
        from server import secure_read_file
        assert callable(secure_read_file)

    def test_import_safe_file_writer(self):
        """SafeFileWriter is importable."""
        from server import SafeFileWriter
        assert SafeFileWriter is not None

    def test_import_write_result(self):
        """WriteResult is importable."""
        from server import WriteResult
        assert WriteResult is not None

    def test_import_secure_write_file(self):
        """secure_write_file is importable."""
        from server import secure_write_file
        assert callable(secure_write_file)

    def test_import_secrets_sanitizer(self):
        """secrets_sanitizer is importable."""
        from server import secrets_sanitizer
        assert secrets_sanitizer is not None
        assert hasattr(secrets_sanitizer, 'sanitize')


class TestConfigImports:
    """Test config imports."""

    def test_import_config(self):
        """config is importable."""
        from server import config
        assert config is not None
        assert hasattr(config, 'sandbox_root')


class TestLoggingImports:
    """Test logging imports."""

    def test_import_log_activity(self):
        """log_activity is importable."""
        from server import log_activity
        assert callable(log_activity)

    def test_import_log_progress(self):
        """log_progress is importable."""
        from server import log_progress
        assert callable(log_progress)

    def test_import_structured_logger(self):
        """structured_logger is importable."""
        from server import structured_logger
        assert structured_logger is not None


class TestGeminiClientImports:
    """Test Gemini client imports."""

    def test_import_client(self):
        """client is importable."""
        from server import client
        # May be None if no API key
        assert True  # Just test import works

    def test_import_types(self):
        """types is importable."""
        from server import types
        assert types is not None

    def test_import_models(self):
        """MODELS is importable."""
        from server import MODELS
        assert isinstance(MODELS, dict)

    def test_import_generate_with_fallback(self):
        """generate_with_fallback is importable."""
        from server import generate_with_fallback
        assert callable(generate_with_fallback)


class TestPersistenceImports:
    """Test persistence imports."""

    def test_import_conversation_memory(self):
        """conversation_memory is importable."""
        from server import conversation_memory
        assert conversation_memory is not None

    def test_import_conversation_thread(self):
        """ConversationThread is importable."""
        from server import ConversationThread
        assert ConversationThread is not None


class TestUtilityImports:
    """Test utility imports."""

    def test_import_expand_file_references(self):
        """expand_file_references is importable."""
        from server import expand_file_references
        assert callable(expand_file_references)

    def test_import_add_line_numbers(self):
        """add_line_numbers is importable."""
        from server import add_line_numbers
        assert callable(add_line_numbers)

    def test_import_estimate_tokens(self):
        """estimate_tokens is importable."""
        from server import estimate_tokens
        assert callable(estimate_tokens)

    def test_import_check_prompt_size(self):
        """check_prompt_size is importable."""
        from server import check_prompt_size
        assert callable(check_prompt_size)


class TestCodeGenerationImports:
    """Test code generation imports."""

    def test_import_parse_generated_code(self):
        """parse_generated_code is importable."""
        from server import parse_generated_code
        assert callable(parse_generated_code)


class TestValidationImports:
    """Test validation imports."""

    def test_import_validate_tool_input(self):
        """validate_tool_input is importable."""
        from server import validate_tool_input
        assert callable(validate_tool_input)


class TestVersionInfo:
    """Test version info."""

    def test_version_defined(self):
        """__version__ is defined and is v3.x."""
        from server import __version__
        assert __version__.startswith("3.")  # v3.0.0, 3.0.1, 3.0.2, etc.


class TestMainFunction:
    """Test main function."""

    def test_main_is_callable(self):
        """main() is callable."""
        from server import main
        assert callable(main)


class TestFunctionalityWorks:
    """Test that imported functions actually work."""

    def test_expand_file_references_works(self):
        """expand_file_references can be called."""
        from server import expand_file_references

        # Text without @ references should pass through
        text = "Hello world"
        result = expand_file_references(text)
        assert result == text

    def test_add_line_numbers_works(self):
        """add_line_numbers can be called."""
        from server import add_line_numbers

        content = "line1\nline2\nline3"
        result = add_line_numbers(content)

        assert "1" in result
        assert "line1" in result

    def test_estimate_tokens_works(self):
        """estimate_tokens can be called."""
        from server import estimate_tokens

        text = "Hello world"
        result = estimate_tokens(text)
        assert isinstance(result, int)
        assert result > 0

    def test_check_prompt_size_works(self):
        """check_prompt_size can be called."""
        from server import check_prompt_size

        # Small text should pass
        result = check_prompt_size("Hello")
        assert result is None  # None means OK
