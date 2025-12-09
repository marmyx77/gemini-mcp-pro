"""
Ask Gemini Tool

Text generation with model selection, thinking capabilities, and conversation memory.
"""

import re
from typing import Optional

from ...tools.registry import tool
from ...services import (
    types,
    MODELS,
    generate_with_fallback,
    conversation_memory,
    CONVERSATION_MAX_TURNS,
)
from ...utils.file_refs import expand_file_references
from ...utils.tokens import check_prompt_size
from ...schemas.inputs import AskGeminiInput


ASK_GEMINI_SCHEMA = {
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


@tool(
    name="ask_gemini",
    description="Ask Gemini a question with optional model selection. Supports multi-turn conversations via continuation_id.",
    input_schema=ASK_GEMINI_SCHEMA,
    input_model=AskGeminiInput,
    tags=["text", "conversation"]
)
def ask_gemini(
    prompt: str,
    model: str = "pro",
    temperature: float = 0.5,
    thinking_level: str = "off",
    include_thoughts: bool = False,
    continuation_id: Optional[str] = None
) -> str:
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

    # Check prompt size after file expansion
    size_error = check_prompt_size(prompt)
    if size_error:
        return f"**Error**: {size_error['message']}"

    # Extract file references from expanded prompt for tracking
    files_referenced = []
    if '@' in original_prompt:
        file_refs = re.findall(r'(?<![a-zA-Z0-9])@([^\s@]+)', original_prompt)
        files_referenced = [ref for ref in file_refs if '@' not in ref]  # Exclude emails

    # Handle conversation memory
    thread_id, is_new, thread = conversation_memory.get_or_create_thread(
        continuation_id=continuation_id,
        metadata={"tool": "ask_gemini", "model": model}
    )

    # Build conversation context if continuing
    conversation_context = ""
    if not is_new:
        conversation_context = conversation_memory.build_context(thread_id)

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
    turn_count = len(conversation_memory.get_thread_history(thread_id))
    output += f"\n\n---\n*continuation_id: {thread_id}* (turn {turn_count}/{CONVERSATION_MAX_TURNS})"

    return output
