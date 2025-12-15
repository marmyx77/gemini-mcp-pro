"""
Conversation Management Tools (v3.3.0)

Tools for listing, searching, and managing Gemini conversation history.
"""

from typing import Optional
from datetime import datetime

from ...tools.registry import tool
from ...services import conversation_memory


# ==================== List Conversations ====================

LIST_CONVERSATIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["all", "local", "cloud"],
            "description": "Filter by conversation mode: 'all' (default), 'local' (SQLite), 'cloud' (Interactions API)",
            "default": "all"
        },
        "search": {
            "type": "string",
            "description": "Search in conversation titles and first prompts"
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results (default: 20)",
            "default": 20
        }
    }
}


@tool(
    name="gemini_list_conversations",
    description="List all Gemini conversations. Shows title, mode (local/cloud), last activity, and turn count. Use to find and resume previous conversations.",
    input_schema=LIST_CONVERSATIONS_SCHEMA,
    tags=["conversation", "management"]
)
def list_conversations(
    mode: str = "all",
    search: Optional[str] = None,
    limit: int = 20
) -> str:
    """
    List conversations from the index.

    Args:
        mode: Filter by mode - "all", "local", or "cloud"
        search: Search term for titles and prompts
        limit: Maximum results to return

    Returns:
        Formatted table of conversations
    """
    # Convert "all" to None for the query
    mode_filter = None if mode == "all" else mode

    conversations = conversation_memory.list_conversations(
        mode=mode_filter,
        search=search,
        limit=limit
    )

    if not conversations:
        if search:
            return f"No conversations found matching '{search}'."
        return "No conversations found. Start a new conversation with ask_gemini."

    # Format output as table
    lines = ["**Gemini Conversations**\n"]

    if search:
        lines.append(f"*Search: '{search}'*\n")

    lines.append("| # | Title | Mode | Last Activity | Turns |")
    lines.append("|---|-------|------|---------------|-------|")

    for i, conv in enumerate(conversations, 1):
        # Format last activity as relative time
        last_used = conv.get("last_used_at", "")
        if last_used:
            try:
                dt = datetime.fromisoformat(last_used)
                delta = datetime.utcnow() - dt
                if delta.days > 0:
                    time_str = f"{delta.days}d ago"
                elif delta.seconds > 3600:
                    time_str = f"{delta.seconds // 3600}h ago"
                elif delta.seconds > 60:
                    time_str = f"{delta.seconds // 60}m ago"
                else:
                    time_str = "just now"
            except Exception:
                time_str = last_used[:10]
        else:
            time_str = "-"

        title = conv.get("title", "Untitled")[:40]
        if len(conv.get("title", "")) > 40:
            title += "..."

        mode_icon = "☁️" if conv.get("mode") == "cloud" else "💾"
        turn_count = conv.get("turn_count", 0)

        lines.append(f"| {i} | {title} | {mode_icon} {conv.get('mode', 'local')} | {time_str} | {turn_count} |")

    lines.append("")
    lines.append("*Use `continuation_id` from a conversation to resume it with ask_gemini.*")
    lines.append("*💾 = local (SQLite), ☁️ = cloud (55-day retention)*")

    # Add IDs for reference
    lines.append("\n**Conversation IDs:**")
    for i, conv in enumerate(conversations, 1):
        lines.append(f"{i}. `{conv.get('id')}`")

    return "\n".join(lines)


# ==================== Delete Conversation ====================

DELETE_CONVERSATION_SCHEMA = {
    "type": "object",
    "properties": {
        "conversation_id": {
            "type": "string",
            "description": "The conversation ID to delete (from gemini_list_conversations)"
        },
        "title": {
            "type": "string",
            "description": "Alternative: delete by title (partial match supported)"
        }
    }
}


@tool(
    name="gemini_delete_conversation",
    description="Delete a Gemini conversation from history. Can delete by ID or title.",
    input_schema=DELETE_CONVERSATION_SCHEMA,
    tags=["conversation", "management"]
)
def delete_conversation(
    conversation_id: Optional[str] = None,
    title: Optional[str] = None
) -> str:
    """
    Delete a conversation from the index and storage.

    Args:
        conversation_id: The conversation ID to delete
        title: Alternative - find and delete by title

    Returns:
        Confirmation message
    """
    if not conversation_id and not title:
        return "**Error**: Please provide either conversation_id or title."

    # Find by title if ID not provided
    if not conversation_id and title:
        conv = conversation_memory.get_conversation_by_title(title)
        if not conv:
            return f"**Error**: No conversation found matching '{title}'."
        conversation_id = conv.get("id")
        found_title = conv.get("title")
    else:
        found_title = title or conversation_id

    # Delete the conversation
    success = conversation_memory.delete_from_index(conversation_id)

    if success:
        return f"✅ Deleted conversation: '{found_title}'"
    else:
        return f"**Error**: Could not delete conversation '{conversation_id}'. It may not exist."
