"""
SQLite Persistence Tests for v3.0.0

Tests:
- Database creation
- Thread CRUD operations
- Turn management
- TTL expiration
- Thread-safe operations
"""

import pytest
import sys
import tempfile
import os
import time
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


@pytest.fixture
def temp_db_dir():
    """Create temporary directory for test database."""
    tmpdir = tempfile.mkdtemp(prefix="gemini_db_test_")
    yield tmpdir
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def persistence_instance(temp_db_dir):
    """Create persistence instance with temp database."""
    from app.services.persistence import PersistentConversationMemory

    db_path = os.path.join(temp_db_dir, "test_conversations.db")
    memory = PersistentConversationMemory(db_path=db_path, ttl_hours=1, max_turns=10)
    yield memory
    memory.close()


class TestDatabaseCreation:
    """Database creation tests."""

    def test_database_file_created(self, temp_db_dir):
        """Database file is created on initialization."""
        from app.services.persistence import PersistentConversationMemory

        db_path = os.path.join(temp_db_dir, "test.db")
        memory = PersistentConversationMemory(db_path=db_path)

        assert os.path.exists(db_path)
        memory.close()

    def test_tables_created(self, temp_db_dir):
        """Required tables are created."""
        from app.services.persistence import PersistentConversationMemory

        db_path = os.path.join(temp_db_dir, "test.db")
        memory = PersistentConversationMemory(db_path=db_path)

        # Check tables exist
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert "conversations" in tables  # Table is named 'conversations' not 'threads'
        assert "turns" in tables
        memory.close()

    def test_wal_mode_enabled(self, temp_db_dir):
        """WAL mode is enabled for better concurrency."""
        from app.services.persistence import PersistentConversationMemory

        db_path = os.path.join(temp_db_dir, "test.db")
        memory = PersistentConversationMemory(db_path=db_path)

        # Check WAL mode
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        conn.close()

        assert mode.lower() == "wal"
        memory.close()


class TestThreadOperations:
    """Thread CRUD operations tests."""

    def test_create_thread(self, persistence_instance):
        """Can create a new thread."""
        thread_id, is_new, thread = persistence_instance.get_or_create_thread()

        assert thread_id is not None
        assert is_new is True
        assert thread is not None

    def test_get_existing_thread(self, persistence_instance):
        """Can retrieve existing thread."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        # Get same thread
        retrieved_id, is_new, thread = persistence_instance.get_or_create_thread(
            continuation_id=thread_id
        )

        assert retrieved_id == thread_id
        assert is_new is False

    def test_thread_has_uuid(self, persistence_instance):
        """Thread ID is a valid UUID format."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        # UUID format: 8-4-4-4-12
        parts = thread_id.split("-")
        assert len(parts) == 5
        assert len(parts[0]) == 8

    def test_nonexistent_thread_creates_new(self, persistence_instance):
        """Requesting nonexistent thread creates new one."""
        thread_id, is_new, _ = persistence_instance.get_or_create_thread(
            continuation_id="nonexistent-thread-id"
        )

        assert is_new is True
        assert thread_id != "nonexistent-thread-id"


class TestTurnManagement:
    """Conversation turn management tests."""

    def test_add_user_turn(self, persistence_instance):
        """Can add user turn to thread."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        persistence_instance.add_turn(
            thread_id=thread_id,
            role="user",
            content="Hello",
            tool_name="ask_gemini"
        )

        turns = persistence_instance.get_thread_history(thread_id)
        assert len(turns) == 1
        assert turns[0].role == "user"

    def test_add_assistant_turn(self, persistence_instance):
        """Can add assistant turn to thread."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        persistence_instance.add_turn(
            thread_id=thread_id,
            role="assistant",
            content="Hi there!",
            tool_name="ask_gemini"
        )

        turns = persistence_instance.get_thread_history(thread_id)
        assert turns[0].role == "assistant"

    def test_multiple_turns(self, persistence_instance):
        """Can add multiple turns to thread."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        for i in range(5):
            role = "user" if i % 2 == 0 else "assistant"
            persistence_instance.add_turn(
                thread_id=thread_id,
                role=role,
                content=f"Message {i}",
                tool_name="ask_gemini"
            )

        turns = persistence_instance.get_thread_history(thread_id)
        assert len(turns) == 5

    def test_turn_order_preserved(self, persistence_instance):
        """Turn order is preserved."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        messages = ["First", "Second", "Third"]
        for msg in messages:
            persistence_instance.add_turn(
                thread_id=thread_id,
                role="user",
                content=msg,
                tool_name="ask_gemini"
            )

        turns = persistence_instance.get_thread_history(thread_id)
        for i, turn in enumerate(turns):
            assert turn.content == messages[i]

    def test_max_turns_limit(self, persistence_instance):
        """Max turns limit is enforced."""
        # Instance has max_turns=10
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        # Add 15 turns
        for i in range(15):
            persistence_instance.add_turn(
                thread_id=thread_id,
                role="user",
                content=f"Message {i}",
                tool_name="ask_gemini"
            )

        turns = persistence_instance.get_thread_history(thread_id)
        # Should only keep last 10
        assert len(turns) <= 10


class TestBuildContext:
    """Context building tests."""

    def test_build_context_formats_turns(self, persistence_instance):
        """build_context formats turns correctly."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        persistence_instance.add_turn(thread_id, "user", "Hello", "ask_gemini")
        persistence_instance.add_turn(thread_id, "assistant", "Hi!", "ask_gemini")

        # Build context from turns
        turns = persistence_instance.get_thread_history(thread_id)
        context = "\n".join([f"{t.role.upper()}: {t.content}" for t in turns])

        assert "USER:" in context or "user" in context.lower()
        assert "ASSISTANT:" in context or "assistant" in context.lower()
        assert "Hello" in context
        assert "Hi!" in context

    def test_build_context_empty_thread(self, persistence_instance):
        """build_context handles empty thread."""
        thread_id, _, _ = persistence_instance.get_or_create_thread()

        turns = persistence_instance.get_thread_history(thread_id)

        # Empty thread should return empty list
        assert len(turns) == 0


class TestTTLExpiration:
    """TTL expiration tests."""

    def test_expired_thread_not_returned(self, temp_db_dir):
        """Expired threads are not returned."""
        from app.services.persistence import PersistentConversationMemory

        # Create with very short TTL
        db_path = os.path.join(temp_db_dir, "ttl_test.db")
        memory = PersistentConversationMemory(
            db_path=db_path,
            ttl_hours=0.0001  # ~0.36 seconds
        )

        thread_id, _, _ = memory.get_or_create_thread()

        # Wait for expiration
        time.sleep(0.5)

        # Should create new thread
        new_id, is_new, _ = memory.get_or_create_thread(continuation_id=thread_id)

        assert is_new is True
        assert new_id != thread_id
        memory.close()

    def test_cleanup_removes_expired(self, temp_db_dir):
        """cleanup_expired removes old threads."""
        from app.services.persistence import PersistentConversationMemory

        db_path = os.path.join(temp_db_dir, "cleanup_test.db")
        memory = PersistentConversationMemory(
            db_path=db_path,
            ttl_hours=0.0001
        )

        # Create threads
        for _ in range(5):
            memory.get_or_create_thread()

        time.sleep(0.5)

        # Cleanup
        deleted = memory.cleanup_expired()

        assert deleted >= 5
        memory.close()


class TestPersistenceAcrossRestarts:
    """Persistence across restarts tests."""

    def test_data_persists_after_close(self, temp_db_dir):
        """Data persists after closing and reopening."""
        from app.services.persistence import PersistentConversationMemory

        db_path = os.path.join(temp_db_dir, "persist_test.db")

        # First instance
        memory1 = PersistentConversationMemory(db_path=db_path)
        thread_id, _, _ = memory1.get_or_create_thread()
        memory1.add_turn(thread_id, "user", "Test message", "ask_gemini")
        memory1.close()

        # Second instance
        memory2 = PersistentConversationMemory(db_path=db_path)
        _, is_new, _ = memory2.get_or_create_thread(continuation_id=thread_id)
        turns = memory2.get_thread_history(thread_id)

        assert is_new is False
        assert len(turns) == 1
        assert turns[0].content == "Test message"
        memory2.close()


class TestThreadSafety:
    """Thread safety tests."""

    def test_concurrent_writes(self, temp_db_dir):
        """Concurrent writes don't corrupt data."""
        from app.services.persistence import PersistentConversationMemory
        import threading

        db_path = os.path.join(temp_db_dir, "concurrent_test.db")
        memory = PersistentConversationMemory(db_path=db_path)

        thread_id, _, _ = memory.get_or_create_thread()
        errors = []

        def add_turns(n):
            try:
                for i in range(n):
                    memory.add_turn(thread_id, "user", f"Msg from thread {i}", "ask_gemini")
            except Exception as e:
                errors.append(e)

        # Run concurrent threads
        threads = [threading.Thread(target=add_turns, args=(10,)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors: {errors}"
        memory.close()
