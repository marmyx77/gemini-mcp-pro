"""Services layer for Gemini integration."""

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

# Conversation memory (SQLite persistence)
from .persistence import (
    PersistentConversationMemory,
    conversation_memory,
    ConversationTurn,
    CONVERSATION_TTL_HOURS,
    CONVERSATION_MAX_TURNS,
)


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
    # Conversation memory (SQLite)
    "PersistentConversationMemory",
    "conversation_memory",
    "ConversationTurn",
    "CONVERSATION_TTL_HOURS",
    "CONVERSATION_MAX_TURNS",
]
