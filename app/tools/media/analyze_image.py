"""
Analyze Image Tool

Image analysis using Gemini vision capabilities.
"""

import os

from ...tools.registry import tool
from ...services import types, MODELS, generate_with_fallback


ANALYZE_IMAGE_SCHEMA = {
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


@tool(
    name="gemini_analyze_image",
    description="Analyze an image using Gemini vision capabilities. Describe, extract text, identify objects, or answer questions about images.",
    input_schema=ANALYZE_IMAGE_SCHEMA,
    tags=["media", "vision"]
)
def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail",
    model: str = "flash"
) -> str:
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
        response = generate_with_fallback(
            model_id=model_id,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=4096
            ),
            operation="analyze_image"
        )

        return response.text

    except Exception as e:
        return f"Image analysis error: {str(e)}"
