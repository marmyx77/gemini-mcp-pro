"""Token estimation utilities."""

from typing import Optional, Dict


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    Uses approximation: 1 token ≈ 4 characters.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4


def check_prompt_size(text: str, limit: int = 60_000) -> Optional[Dict[str, str]]:
    """
    Check if prompt exceeds MCP transport limit.

    Args:
        text: Prompt text to check
        limit: Maximum character limit (default 60,000)

    Returns:
        Error dict if too large, None if OK.
    """
    if len(text) > limit:
        return {
            "status": "error",
            "message": f"Prompt too large ({len(text):,} chars, limit {limit:,}). "
                      f"Save content to file and reference with @filename instead."
        }
    return None
