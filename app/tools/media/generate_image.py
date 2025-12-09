"""
Generate Image Tool

Image generation using Gemini native image generation.
"""

import base64
from typing import Optional

from ...tools.registry import tool
from ...services import types, IMAGE_MODELS, client
from ...core import log_progress


GENERATE_IMAGE_SCHEMA = {
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


@tool(
    name="gemini_generate_image",
    description="Generate an image using Gemini native image generation. Defaults to Gemini 3 Pro for best quality. Use descriptive prompts (not keywords).",
    input_schema=GENERATE_IMAGE_SCHEMA,
    tags=["media", "generation"]
)
def generate_image(
    prompt: str,
    model: str = "pro",
    aspect_ratio: str = "1:1",
    image_size: str = "2K",
    output_path: Optional[str] = None
) -> str:
    """
    Generate image using Gemini native image generation.
    Defaults to Gemini 3 Pro for best quality.

    Models:
    - pro: gemini-3-pro-image-preview (high quality, up to 4K, thinking mode) - DEFAULT
    - flash: gemini-2.5-flash-image (fast, 1024px max)
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

        log_progress(f"Generating {image_size} image with {model_id}...")

        response = client.models.generate_content(
            model=model_id,
            contents=prompt,
            config=types.GenerateContentConfig(**config_params)
        )

        log_progress("Image generation completed")

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
