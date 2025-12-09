"""Services layer for Gemini integration."""

import warnings

from .gemini import (
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

# v3.0.0: Use persistent memory (SQLite) as primary
from .persistence import (
    PersistentConversationMemory,
    conversation_memory,  # This is now the main instance
    CONVERSATION_TTL_HOURS,
    CONVERSATION_MAX_TURNS,
)

# Legacy in-memory classes (deprecated)
# Import but mark as deprecated
from .memory import (
    ConversationTurn,
    ConversationThread,
    ConversationMemory as _LegacyConversationMemory,
)


def ConversationMemory(*args, **kwargs):
    """
    DEPRECATED: Use PersistentConversationMemory instead.

    This wrapper exists for backward compatibility only.
    Will be removed in v4.0.0.
    """
    warnings.warn(
        "ConversationMemory is deprecated since v3.0.0. "
        "Use PersistentConversationMemory instead. "
        "This class will be removed in v4.0.0.",
        DeprecationWarning,
        stacklevel=2
    )
    return _LegacyConversationMemory(*args, **kwargs)


__all__ = [
    # Gemini client
    "client",
    "types",
    "MODELS",
    "IMAGE_MODELS",
    "VIDEO_MODELS",
    "TTS_MODELS",
    "TTS_VOICES",
    "generate_with_fallback",
    "is_available",
    "get_error",
    # Conversation memory (SQLite, v3.0.0 - primary)
    "PersistentConversationMemory",
    "conversation_memory",
    "CONVERSATION_TTL_HOURS",
    "CONVERSATION_MAX_TURNS",
    # Legacy classes (deprecated, for backward compatibility)
    "ConversationTurn",
    "ConversationThread",
    "ConversationMemory",
]
