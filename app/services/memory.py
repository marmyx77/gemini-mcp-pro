"""
Conversation Memory System

DEPRECATED: This module is deprecated since v3.0.0.
Use app.services.persistence.PersistentConversationMemory instead.
This module provides in-memory storage that does NOT survive restarts.
It will be removed in v4.0.0.

Thread-safe in-memory storage for multi-turn conversations with Gemini.
Supports TTL-based expiration and automatic cleanup.
"""

import warnings
import threading

# Issue deprecation warning on import
warnings.warn(
    "app.services.memory is deprecated since v3.0.0. "
    "Use app.services.persistence.PersistentConversationMemory instead. "
    "In-memory conversations do NOT survive server restarts. "
    "This module will be removed in v4.0.0.",
    DeprecationWarning,
    stacklevel=2
)
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..core import config, log_progress

# Configuration
CONVERSATION_TTL_HOURS = config.conversation_ttl_hours
CONVERSATION_MAX_TURNS = config.conversation_max_turns
CONVERSATION_CLEANUP_INTERVAL = max(300, (CONVERSATION_TTL_HOURS * 3600) // 10)


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    tool_name: str = None
    files_referenced: List[str] = field(default_factory=list)


@dataclass
class ConversationThread:
    """A conversation thread with multiple turns."""
    thread_id: str
    created_at: datetime
    last_activity: datetime
    turns: List[ConversationTurn] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if thread has expired based on TTL."""
        expiry = self.last_activity + timedelta(hours=CONVERSATION_TTL_HOURS)
        return datetime.now() > expiry

    def can_add_turn(self) -> bool:
        """Check if we can add more turns."""
        return len(self.turns) < CONVERSATION_MAX_TURNS

    def add_turn(
        self,
        role: str,
        content: str,
        tool_name: str = None,
        files: List[str] = None
    ) -> bool:
        """Add a turn to the conversation."""
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

        # Estimate tokens (rough: 1 token ~ 4 chars)
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
        """Initialize the memory storage."""
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
        """Create a new conversation thread."""
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
        """Get a thread by ID, returns None if expired or not found."""
        with self._storage_lock:
            thread = self._threads.get(thread_id)
            if thread is None:
                return None

            if thread.is_expired():
                del self._threads[thread_id]
                return None

            return thread

    def add_turn(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_name: str = None,
        files: List[str] = None
    ) -> bool:
        """Add a turn to an existing thread."""
        thread = self.get_thread(thread_id)
        if thread is None:
            return False

        with self._storage_lock:
            return thread.add_turn(role, content, tool_name, files)

    def get_or_create_thread(
        self,
        continuation_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> tuple:
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
        """Background thread for cleaning up expired threads."""
        while not self._shutdown:
            time.sleep(CONVERSATION_CLEANUP_INTERVAL)
            self._cleanup_expired()

    def _cleanup_expired(self):
        """Remove all expired threads."""
        with self._storage_lock:
            expired = [tid for tid, t in self._threads.items() if t.is_expired()]
            for tid in expired:
                del self._threads[tid]

            if expired:
                log_progress(f"Cleaned up {len(expired)} expired conversation thread(s)")

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._storage_lock:
            return {
                "active_threads": len(self._threads),
                "ttl_hours": CONVERSATION_TTL_HOURS,
                "max_turns": CONVERSATION_MAX_TURNS
            }


# Global conversation memory instance
conversation_memory = ConversationMemory()
