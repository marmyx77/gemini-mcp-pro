#!/usr/bin/env python3
"""
gemini-mcp-pro v1.1.0
Full-featured MCP server for Google Gemini: text generation with thinking mode,
web search, RAG, image analysis, image generation, video generation, text-to-speech
"""

import json
import sys
import os
import base64
import time
import wave
from typing import Dict, Any, Optional, List

# Ensure unbuffered output for MCP JSON-RPC communication
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    # Fallback for older Python versions
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 1)
    sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', 1)

__version__ = "1.1.0"

# Model mapping - Gemini 3 Pro prioritized for advanced reasoning
# Use "fast" for high-volume, low-reasoning tasks
MODELS = {
    "pro": "gemini-3-pro-preview",       # Best for reasoning, coding, complex tasks
    "flash": "gemini-2.5-flash",          # Balanced speed/quality for standard tasks
    "fast": "gemini-2.5-flash",           # High-volume, simple tasks (same as flash, lower cost tier)
}

# Image models
IMAGE_MODELS = {
    "pro": "gemini-3-pro-image-preview",  # High quality, 4K, thinking mode
    "flash": "gemini-2.5-flash-image",    # Fast generation
}

# Video models - Veo 3.1 for state-of-the-art video generation with audio
VIDEO_MODELS = {
    "veo31": "veo-3.1-generate-preview",       # Best quality, 8s, 720p/1080p, audio
    "veo31_fast": "veo-3.1-fast-generate-preview",  # Faster, optimized for speed
    "veo3": "veo-3.0-generate-001",            # Stable, 8s with audio
    "veo3_fast": "veo-3.0-fast-generate-001",  # Fast stable version
    "veo2": "veo-2.0-generate-001",            # Legacy, no audio
}

# TTS models - Native text-to-speech
TTS_MODELS = {
    "flash": "gemini-2.5-flash-preview-tts",  # Fast TTS
    "pro": "gemini-2.5-pro-preview-tts",      # Higher quality TTS
}

# Available TTS voices with their characteristics
TTS_VOICES = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm",
}

# Initialize Gemini
GEMINI_AVAILABLE = False
GEMINI_ERROR = ""
client = None

try:
    from google import genai
    from google.genai import types

    API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
        GEMINI_ERROR = "Please set GEMINI_API_KEY environment variable"
    else:
        client = genai.Client(api_key=API_KEY)
        GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_ERROR = "google-genai SDK not installed. Run: pip install google-genai"
except Exception:
    # Don't expose internal error details that might leak sensitive info
    GEMINI_ERROR = "Failed to initialize Gemini client. Check your API key."


def send_response(response: Dict[str, Any]):
    """Send a JSON-RPC response"""
    print(json.dumps(response), flush=True)


def handle_initialize(request_id: Any) -> Dict[str, Any]:
    """Handle initialization"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "gemini-mcp-pro",
                "version": __version__
            }
        }
    }


def get_tools_list() -> List[Dict[str, Any]]:
    """Return available tools based on Gemini availability"""
    if not GEMINI_AVAILABLE:
        return [{
            "name": "server_status",
            "description": f"Server error: {GEMINI_ERROR}",
            "inputSchema": {"type": "object", "properties": {}}
        }]

    return [
        {
            "name": "ask_gemini",
            "description": "Ask Gemini a question with optional model selection",
            "inputSchema": {
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
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_code_review",
            "description": "Have Gemini review code with specific focus. Uses Gemini 3 Pro for best reasoning.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Code to review"},
                    "focus": {
                        "type": "string",
                        "description": "Focus area: security, performance, readability, bugs, general",
                        "default": "general"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Gemini 3 Pro - thorough analysis. flash: faster but less detailed",
                        "default": "pro"
                    }
                },
                "required": ["code"]
            }
        },
        {
            "name": "gemini_brainstorm",
            "description": "Brainstorm ideas with Gemini. Uses Gemini 3 Pro for creative reasoning.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic to brainstorm"},
                    "context": {"type": "string", "description": "Additional context", "default": ""}
                },
                "required": ["topic"]
            }
        },
        {
            "name": "gemini_web_search",
            "description": "Search the web using Gemini with Google Search grounding. Returns answers with citations.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro: Gemini 3 Pro - better synthesis. flash (default): faster for simple queries",
                        "default": "flash"
                    }
                },
                "required": ["query"]
            }
        },
        {
            "name": "gemini_create_file_store",
            "description": "Create a File Search Store for RAG. Use this before uploading files.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Display name for the store"}
                },
                "required": ["name"]
            }
        },
        {
            "name": "gemini_upload_file",
            "description": "Upload a file to a File Search Store for RAG queries",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Local file path to upload"},
                    "store_name": {"type": "string", "description": "File Search Store name (from create_file_store)"}
                },
                "required": ["file_path", "store_name"]
            }
        },
        {
            "name": "gemini_file_search",
            "description": "Query documents in a File Search Store using RAG",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Question to ask about the documents"},
                    "store_name": {"type": "string", "description": "File Search Store name"}
                },
                "required": ["question", "store_name"]
            }
        },
        {
            "name": "gemini_analyze_image",
            "description": "Analyze an image using Gemini vision capabilities. Describe, extract text, identify objects, or answer questions about images.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Local file path to the image (supports PNG, JPG, JPEG, GIF, WEBP)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "What to do with the image: 'describe', 'extract text', or a specific question",
                        "default": "Describe this image in detail"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "flash (default): Gemini 2.5 Flash - reliable vision. pro: Gemini 3 Pro (experimental)",
                        "default": "flash"
                    }
                },
                "required": ["image_path"]
            }
        },
        {
            "name": "gemini_generate_image",
            "description": "Generate an image using Gemini native image generation. Defaults to Gemini 3 Pro for best quality. Use descriptive prompts (not keywords).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed image description. Be specific: describe scene, lighting, style, camera angle. Example: 'A photorealistic close-up portrait of an elderly ceramicist with warm lighting, captured with 85mm lens'"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["pro", "flash"],
                        "description": "pro (default): Gemini 3 Pro - high quality, 4K, thinking mode. flash: Gemini 2.5 Flash - fast generation",
                        "default": "pro"
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["1:1", "2:3", "3:2", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"],
                        "description": "Output aspect ratio",
                        "default": "1:1"
                    },
                    "image_size": {
                        "type": "string",
                        "enum": ["1K", "2K", "4K"],
                        "description": "Resolution (only for pro model). 1K=1024px, 2K=2048px, 4K=4096px",
                        "default": "2K"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save image (optional, returns base64 preview if not provided)"
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_list_file_stores",
            "description": "List all available File Search Stores",
            "inputSchema": {
                "type": "object",
                "properties": {}
            }
        },
        {
            "name": "gemini_generate_video",
            "description": "Generate a video using Google Veo 3.1 with native audio. Creates 4-8 second 720p/1080p videos with realistic motion, dialogue, and sound effects. Use descriptive prompts including subject, action, style, camera motion.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed video description. Include: subject, action, style, camera motion, ambiance. For dialogue use quotes: 'Hello,' she said. For sounds describe explicitly: engine roaring, birds chirping."
                    },
                    "model": {
                        "type": "string",
                        "enum": ["veo31", "veo31_fast", "veo3", "veo3_fast", "veo2"],
                        "description": "veo31 (default): Best quality with audio. veo31_fast: Faster. veo3/veo3_fast: Stable versions. veo2: Legacy, no audio.",
                        "default": "veo31"
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "9:16"],
                        "description": "16:9 for landscape (default), 9:16 for portrait/vertical",
                        "default": "16:9"
                    },
                    "duration": {
                        "type": "integer",
                        "enum": [4, 6, 8],
                        "description": "Video duration in seconds. 8s required for 1080p.",
                        "default": 8
                    },
                    "resolution": {
                        "type": "string",
                        "enum": ["720p", "1080p"],
                        "description": "720p (default) or 1080p (Veo 3.1 only, requires 8s duration)",
                        "default": "720p"
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "What NOT to include (e.g., 'cartoon, low quality, blurry'). Don't use 'no' or 'don't'."
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save video (.mp4). If not provided, saves to /tmp/"
                    }
                },
                "required": ["prompt"]
            }
        },
        {
            "name": "gemini_text_to_speech",
            "description": "Convert text to speech using Gemini TTS. Supports single-speaker and multi-speaker (up to 2) audio with 30 voice options. Control style, tone, accent, and pace with natural language.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to convert to speech. Include style instructions like 'Say cheerfully:' or 'Speaker1 sounds tired:'. For multi-speaker, format as 'Speaker1: text\\nSpeaker2: text'"
                    },
                    "voice": {
                        "type": "string",
                        "enum": ["Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede", "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba", "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar", "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi", "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat"],
                        "description": "Voice for single-speaker. Popular: Kore (Firm), Puck (Upbeat), Charon (Informative), Aoede (Breezy), Sulafat (Warm)",
                        "default": "Kore"
                    },
                    "model": {
                        "type": "string",
                        "enum": ["flash", "pro"],
                        "description": "flash (default): Fast TTS. pro: Higher quality",
                        "default": "flash"
                    },
                    "speakers": {
                        "type": "array",
                        "description": "For multi-speaker: [{\"name\": \"Speaker1\", \"voice\": \"Kore\"}, {\"name\": \"Speaker2\", \"voice\": \"Puck\"}]. Max 2 speakers.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "voice": {"type": "string"}
                            }
                        }
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path to save audio (.wav). If not provided, saves to /tmp/"
                    }
                },
                "required": ["text"]
            }
        }
    ]


def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """List available tools"""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {"tools": get_tools_list()}
    }


# ============ Tool Implementations ============

def tool_ask_gemini(prompt: str, model: str = "pro", temperature: float = 0.5,
                    thinking_level: str = "off", include_thoughts: bool = False) -> str:
    """
    Gemini query with model selection and optional thinking capabilities.

    Thinking allows the model to engage in deeper reasoning for complex tasks.
    - For Gemini 3 Pro: uses thinking_level ("low" or "high")
    - For Gemini 2.5: uses thinking_budget (auto-calculated based on level)
    """
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

    response = client.models.generate_content(
        model=model_id,
        contents=prompt,
        config=types.GenerateContentConfig(**config_params)
    )

    # If include_thoughts is enabled, format response with thought summaries
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

        return "\n\n".join(result_parts) if result_parts else response.text

    return response.text


def tool_code_review(code: str, focus: str = "general", model: str = "pro") -> str:
    """Code review with specific focus"""
    prompt = f"""Review this code with focus on {focus}:

```
{code}
```

Provide specific, actionable feedback on:
1. Potential issues or bugs
2. Security concerns
3. Performance optimizations
4. Best practices
5. Code clarity"""

    return tool_ask_gemini(prompt, model=model, temperature=0.2)


def tool_brainstorm(topic: str, context: str = "") -> str:
    """Creative brainstorming using Gemini 3 Pro for best reasoning"""
    prompt = f"Let's brainstorm about: {topic}"
    if context:
        prompt += f"\n\nContext: {context}"
    prompt += "\n\nProvide creative ideas, alternatives, and considerations."

    return tool_ask_gemini(prompt, model="pro", temperature=0.7)


def tool_web_search(query: str, model: str = "flash") -> str:
    """Web search with Google grounding"""
    model_id = MODELS.get(model, MODELS["flash"])

    response = client.models.generate_content(
        model=model_id,
        contents=query,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.3
        )
    )

    result = response.text

    # Extract grounding metadata if available
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                result += "\n\n**Sources:**\n"
                for chunk in metadata.grounding_chunks[:5]:
                    if hasattr(chunk, 'web') and chunk.web:
                        result += f"- [{chunk.web.title}]({chunk.web.uri})\n"

    return result


def tool_create_file_store(name: str) -> str:
    """Create a File Search Store"""
    store = client.file_search_stores.create(
        config={"display_name": name}
    )
    return f"Created File Search Store:\n- Name: {store.name}\n- Display Name: {name}\n\nUse this store_name for uploads and queries: {store.name}"


def tool_upload_file(file_path: str, store_name: str) -> str:
    """Upload file to File Search Store"""
    if not os.path.exists(file_path):
        return f"Error: File not found: {file_path}"

    filename = os.path.basename(file_path)

    operation = client.file_search_stores.upload_to_file_search_store(
        file=file_path,
        file_search_store_name=store_name,
        config={"display_name": filename}
    )

    # Wait for completion (with timeout)
    timeout = 120
    start = time.time()
    while not operation.done and (time.time() - start) < timeout:
        time.sleep(2)
        operation = client.operations.get(operation)

    if operation.done:
        return f"Successfully uploaded '{filename}' to store {store_name}"
    else:
        return f"Upload in progress for '{filename}'. Check back later."


def tool_file_search(question: str, store_name: str) -> str:
    """Query documents using File Search RAG"""
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=question,
        config=types.GenerateContentConfig(
            tools=[
                types.Tool(
                    file_search=types.FileSearch(
                        file_search_store_names=[store_name]
                    )
                )
            ]
        )
    )

    result = response.text

    # Add citations if available
    if hasattr(response, 'candidates') and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
            metadata = candidate.grounding_metadata
            if hasattr(metadata, 'grounding_chunks') and metadata.grounding_chunks:
                result += "\n\n**Citations:**\n"
                for i, chunk in enumerate(metadata.grounding_chunks[:5], 1):
                    if hasattr(chunk, 'retrieved_context'):
                        ctx = chunk.retrieved_context
                        result += f"{i}. {ctx.title if hasattr(ctx, 'title') else 'Document'}\n"

    return result


def tool_list_file_stores() -> str:
    """List all File Search Stores"""
    stores = client.file_search_stores.list()
    if not stores:
        return "No File Search Stores found. Create one with gemini_create_file_store."

    result = "**Available File Search Stores:**\n"
    for store in stores:
        result += f"- {store.display_name}: `{store.name}`\n"
    return result


def tool_analyze_image(image_path: str, prompt: str = "Describe this image in detail",
                       model: str = "flash") -> str:
    """
    Analyze an image using Gemini vision capabilities.

    Supports: PNG, JPG, JPEG, GIF, WEBP
    Use cases: describe images, extract text (OCR), identify objects, answer questions
    """
    try:
        if not os.path.exists(image_path):
            return f"Error: Image not found: {image_path}"

        # Determine MIME type
        ext = os.path.splitext(image_path)[1].lower()
        mime_types = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }

        mime_type = mime_types.get(ext)
        if not mime_type:
            return f"Error: Unsupported image format: {ext}. Supported: PNG, JPG, JPEG, GIF, WEBP"

        # Read image and encode to base64
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Select model
        model_id = MODELS.get(model, MODELS["pro"])

        # Create image part
        image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)

        # Generate response
        response = client.models.generate_content(
            model=model_id,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096
            )
        )

        return response.text

    except Exception as e:
        return f"Image analysis error: {str(e)}"


def tool_generate_image(prompt: str, model: str = "pro", aspect_ratio: str = "1:1",
                        image_size: str = "2K", output_path: str = None) -> str:
    """
    Generate image using Gemini native image generation.
    Defaults to Gemini 3 Pro for best quality.

    Models:
    - pro: gemini-3-pro-image-preview (high quality, up to 4K, thinking mode) - DEFAULT
    - flash: gemini-2.5-flash-image (fast, 1024px max)

    Best practices:
    - Use descriptive prompts, not keyword lists
    - Specify style, lighting, camera angle, mood
    - For photorealism: mention lens type, lighting setup
    - For illustrations: specify art style, line style, colors
    """
    try:
        # Select model - default to Pro for best quality
        model_id = IMAGE_MODELS.get(model, IMAGE_MODELS["pro"])

        # Build config
        config_params = {
            "response_modalities": ["IMAGE", "TEXT"]
        }

        # Add image config for aspect ratio and size
        image_config = {"aspect_ratio": aspect_ratio}

        # image_size only supported by pro model
        if model == "pro" and image_size in ["1K", "2K", "4K"]:
            image_config["image_size"] = image_size

        config_params["image_config"] = types.ImageConfig(**image_config)

        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(**config_params)
        )

        # Look for image in response parts
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'inline_data') and part.inline_data:
                image_data = part.inline_data.data
                mime_type = part.inline_data.mime_type

                # Determine file extension
                ext = ".png"
                if "jpeg" in mime_type:
                    ext = ".jpg"
                elif "webp" in mime_type:
                    ext = ".webp"

                if output_path:
                    # Ensure correct extension
                    if not output_path.endswith(ext):
                        output_path = output_path.rsplit('.', 1)[0] + ext
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                    return f"Image saved to: {output_path}\nModel: {model_id}\nAspect ratio: {aspect_ratio}"
                else:
                    b64 = base64.b64encode(image_data).decode('utf-8')
                    return f"Generated image ({mime_type})\nModel: {model_id}\nAspect ratio: {aspect_ratio}\nBase64 (first 100 chars): {b64[:100]}...\nTotal size: {len(b64)} characters"

        # If no image found, return text response if any
        text_parts = [p.text for p in response.candidates[0].content.parts if hasattr(p, 'text') and p.text]
        if text_parts:
            return f"No image generated. Model response: {' '.join(text_parts)}"
        return "No image generated. Try a more descriptive prompt."

    except Exception as e:
        return f"Image generation error: {str(e)}"


def tool_generate_video(prompt: str, model: str = "veo31", aspect_ratio: str = "16:9",
                        duration: int = 8, resolution: str = "720p",
                        negative_prompt: str = None, output_path: str = None) -> str:
    """
    Generate video using Google Veo 3.1 - state-of-the-art video generation with native audio.

    Models:
    - veo31: Best quality, 720p/1080p, 4-8 seconds, native audio (DEFAULT)
    - veo31_fast: Faster generation, optimized for speed
    - veo3: Stable version with audio
    - veo3_fast: Fast stable version
    - veo2: Legacy, no audio

    Best practices for prompts:
    - Include: subject, action, style, camera motion, composition, ambiance
    - For dialogue: use quotes ("Hello," she said)
    - For sound effects: describe explicitly (tires screeching, engine roaring)
    - For ambient noise: describe environment's soundscape
    """
    try:
        model_id = VIDEO_MODELS.get(model, VIDEO_MODELS["veo31"])

        # Build config
        config_params = {
            "aspect_ratio": aspect_ratio,
            "duration_seconds": str(duration),
        }

        # Resolution only for Veo 3.1 (1080p requires 8s duration)
        if model in ["veo31", "veo31_fast"]:
            if resolution == "1080p" and duration != 8:
                config_params["resolution"] = "720p"  # 1080p requires 8s
            else:
                config_params["resolution"] = resolution

        # Add negative prompt if provided
        if negative_prompt:
            config_params["negative_prompt"] = negative_prompt

        # Person generation - required for Veo
        config_params["person_generation"] = "allow_all"

        # Start video generation
        operation = client.models.generate_videos(
            model=model_id,
            prompt=prompt,
            config=types.GenerateVideosConfig(**config_params)
        )

        # Poll for completion (video generation can take 1-6 minutes)
        max_wait = 360  # 6 minutes max
        poll_interval = 10
        elapsed = 0

        while not operation.done and elapsed < max_wait:
            time.sleep(poll_interval)
            elapsed += poll_interval
            operation = client.operations.get(operation)

        if not operation.done:
            return f"Video generation timed out after {max_wait} seconds. Operation may still be running."

        # Check for errors
        if hasattr(operation, 'error') and operation.error:
            return f"Video generation failed: {operation.error}"

        # Get generated video
        if not hasattr(operation, 'response') or not operation.response:
            return "Video generation completed but no response received."

        generated_videos = operation.response.generated_videos
        if not generated_videos:
            return "No video was generated. Try a different prompt."

        video = generated_videos[0]

        # Download the video
        client.files.download(file=video.video)

        if output_path:
            # Ensure .mp4 extension
            if not output_path.endswith('.mp4'):
                output_path = output_path.rsplit('.', 1)[0] + '.mp4' if '.' in output_path else output_path + '.mp4'

            video.video.save(output_path)

            return f"""Video generated successfully!
- Saved to: {output_path}
- Model: {model_id}
- Duration: {duration}s
- Resolution: {resolution}
- Aspect ratio: {aspect_ratio}
- Has audio: {'Yes' if model != 'veo2' else 'No'}"""
        else:
            # Save to temp location and return info
            temp_path = f"/tmp/gemini_video_{int(time.time())}.mp4"
            video.video.save(temp_path)

            return f"""Video generated successfully!
- Temporary file: {temp_path}
- Model: {model_id}
- Duration: {duration}s
- Resolution: {resolution}
- Aspect ratio: {aspect_ratio}
- Has audio: {'Yes' if model != 'veo2' else 'No'}

Note: Specify output_path to save to a custom location."""

    except Exception as e:
        return f"Video generation error: {str(e)}"


def tool_text_to_speech(text: str, voice: str = "Kore", model: str = "flash",
                        speakers: List[Dict[str, str]] = None,
                        output_path: str = None) -> str:
    """
    Generate speech from text using Gemini TTS.
    Supports single-speaker and multi-speaker (up to 2) audio generation.

    Models:
    - flash: Fast TTS generation (default)
    - pro: Higher quality TTS

    Voices (30 options): Zephyr (Bright), Puck (Upbeat), Charon (Informative),
    Kore (Firm), Fenrir (Excitable), Leda (Youthful), and more.

    For multi-speaker, use the speakers parameter with format:
    [{"name": "Speaker1", "voice": "Kore"}, {"name": "Speaker2", "voice": "Puck"}]

    Style control: Include style instructions in the text prompt, e.g.,
    "Say cheerfully: Hello!" or "Speaker1 sounds tired, Speaker2 sounds excited"
    """
    try:
        model_id = TTS_MODELS.get(model, TTS_MODELS["flash"])

        # Build speech config
        if speakers and len(speakers) >= 2:
            # Multi-speaker mode
            speaker_configs = []
            for speaker in speakers[:2]:  # Max 2 speakers
                speaker_name = speaker.get("name", "Speaker")
                speaker_voice = speaker.get("voice", "Kore")
                # Validate voice
                if speaker_voice not in TTS_VOICES:
                    speaker_voice = "Kore"

                speaker_configs.append(
                    types.SpeakerVoiceConfig(
                        speaker=speaker_name,
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=speaker_voice
                            )
                        )
                    )
                )

            speech_config = types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_configs
                )
            )
        else:
            # Single-speaker mode
            if voice not in TTS_VOICES:
                voice = "Kore"

            speech_config = types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice
                    )
                )
            )

        # Generate audio
        response = client.models.generate_content(
            model=model_id,
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config
            )
        )

        # Extract audio data
        audio_data = response.candidates[0].content.parts[0].inline_data.data

        # Determine output path
        if not output_path:
            output_path = f"/tmp/gemini_tts_{int(time.time())}.wav"
        elif not output_path.endswith('.wav'):
            output_path = output_path.rsplit('.', 1)[0] + '.wav' if '.' in output_path else output_path + '.wav'

        # Save as WAV file (PCM 24kHz, 16-bit, mono)
        with wave.open(output_path, "wb") as wf:
            wf.setnchannels(1)        # Mono
            wf.setsampwidth(2)        # 16-bit
            wf.setframerate(24000)    # 24kHz
            wf.writeframes(audio_data)

        # Calculate duration
        duration_sec = len(audio_data) / (24000 * 2)  # samples / (rate * bytes_per_sample)

        mode = "Multi-speaker" if (speakers and len(speakers) >= 2) else "Single-speaker"
        voice_info = ", ".join([f"{s['name']}: {s['voice']}" for s in speakers[:2]]) if speakers else voice

        return f"""Audio generated successfully!
- Saved to: {output_path}
- Model: {model_id}
- Mode: {mode}
- Voice(s): {voice_info}
- Duration: {duration_sec:.1f}s
- Format: WAV (24kHz, 16-bit, mono)"""

    except Exception as e:
        return f"TTS generation error: {str(e)}"


def handle_tool_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool execution"""
    tool_name = params.get("name")
    args = params.get("arguments", {})

    try:
        if not GEMINI_AVAILABLE:
            result = f"Gemini not available: {GEMINI_ERROR}"
        elif tool_name == "ask_gemini":
            result = tool_ask_gemini(
                args.get("prompt", ""),
                args.get("model", "pro"),
                args.get("temperature", 0.5),
                args.get("thinking_level", "off"),
                args.get("include_thoughts", False)
            )
        elif tool_name == "gemini_code_review":
            result = tool_code_review(
                args.get("code", ""),
                args.get("focus", "general"),
                args.get("model", "pro")
            )
        elif tool_name == "gemini_brainstorm":
            result = tool_brainstorm(
                args.get("topic", ""),
                args.get("context", "")
            )
        elif tool_name == "gemini_web_search":
            result = tool_web_search(
                args.get("query", ""),
                args.get("model", "flash")
            )
        elif tool_name == "gemini_create_file_store":
            result = tool_create_file_store(args.get("name", ""))
        elif tool_name == "gemini_upload_file":
            result = tool_upload_file(
                args.get("file_path", ""),
                args.get("store_name", "")
            )
        elif tool_name == "gemini_file_search":
            result = tool_file_search(
                args.get("question", ""),
                args.get("store_name", "")
            )
        elif tool_name == "gemini_list_file_stores":
            result = tool_list_file_stores()
        elif tool_name == "gemini_analyze_image":
            result = tool_analyze_image(
                args.get("image_path", ""),
                args.get("prompt", "Describe this image in detail"),
                args.get("model", "flash")
            )
        elif tool_name == "gemini_generate_image":
            result = tool_generate_image(
                args.get("prompt", ""),
                args.get("model", "pro"),
                args.get("aspect_ratio", "1:1"),
                args.get("image_size", "2K"),
                args.get("output_path")
            )
        elif tool_name == "gemini_generate_video":
            result = tool_generate_video(
                args.get("prompt", ""),
                args.get("model", "veo31"),
                args.get("aspect_ratio", "16:9"),
                args.get("duration", 8),
                args.get("resolution", "720p"),
                args.get("negative_prompt"),
                args.get("output_path")
            )
        elif tool_name == "gemini_text_to_speech":
            result = tool_text_to_speech(
                args.get("text", ""),
                args.get("voice", "Kore"),
                args.get("model", "flash"),
                args.get("speakers"),
                args.get("output_path")
            )
        elif tool_name == "server_status":
            result = f"Server v{__version__}\nGemini: {'Available' if GEMINI_AVAILABLE else 'Error: ' + GEMINI_ERROR}"
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"**GEMINI ({tool_name}):**\n\n{result}"
                }]
            }
        }
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32603, "message": str(e)}
        }


def main():
    """Main server loop"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line.strip())
            method = request.get("method")
            request_id = request.get("id")
            params = request.get("params", {})

            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "notifications/initialized":
                continue  # No response needed
            elif method == "tools/list":
                response = handle_tools_list(request_id)
            elif method == "tools/call":
                response = handle_tool_call(request_id, params)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }

            send_response(response)

        except json.JSONDecodeError:
            continue
        except EOFError:
            break
        except Exception as e:
            if 'request_id' in locals() and request_id:
                send_response({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
                })


if __name__ == "__main__":
    main()
