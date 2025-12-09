"""Line numbering utilities for code display."""


# File extensions to skip line numbering
SKIP_LINE_NUMBERS = {'.json', '.md', '.txt', '.csv', '.yaml', '.yml', '.toml', '.ini', '.cfg'}


def add_line_numbers(content: str, start_line: int = 1) -> str:
    """
    Add line numbers to content for better code navigation.

    Format: "  42│ actual code here"

    Args:
        content: The text content to number
        start_line: Starting line number (default 1)

    Returns:
        Content with line numbers prefixed
    """
    if not content:
        return content

    lines = content.split('\n')
    total_lines = len(lines) + start_line - 1
    width = len(str(total_lines))

    numbered_lines = []
    for i, line in enumerate(lines, start=start_line):
        numbered_lines.append(f"{i:>{width}}│ {line}")

    return '\n'.join(numbered_lines)


def should_add_line_numbers(filename: str) -> bool:
    """
    Check if file should have line numbers added.

    Args:
        filename: Name or path of the file

    Returns:
        True if line numbers should be added
    """
    import os
    ext = os.path.splitext(filename)[1].lower()
    return ext not in SKIP_LINE_NUMBERS
