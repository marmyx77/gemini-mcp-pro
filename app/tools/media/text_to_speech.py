"""
Text to Speech Tool

Generate speech from text using Gemini TTS.
"""

import time
import wave
from typing import Dict, List, Optional

from ...tools.registry import tool
from ...services import types, TTS_MODELS, TTS_VOICES, client


TEXT_TO_SPEECH_SCHEMA = {
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "Text to convert to speech. Include style instructions like 'Say cheerfully:' or 'Speaker1 sounds tired:'. For multi-speaker, format as 'Speaker1: text\\nSpeaker2: text'"
        },
        "voice": {
            "type": "string",
            "enum": list(TTS_VOICES.keys()),
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
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "voice": {"type": "string"}
                }
            },
            "description": "For multi-speaker: [{\"name\": \"Speaker1\", \"voice\": \"Kore\"}, {\"name\": \"Speaker2\", \"voice\": \"Puck\"}]. Max 2 speakers."
        },
        "output_path": {
            "type": "string",
            "description": "Path to save audio (.wav). If not provided, saves to /tmp/"
        }
    },
    "required": ["text"]
}


@tool(
    name="gemini_text_to_speech",
    description="Convert text to speech using Gemini TTS. Supports single-speaker and multi-speaker (up to 2) audio with 30 voice options. Control style, tone, accent, and pace with natural language.",
    input_schema=TEXT_TO_SPEECH_SCHEMA,
    tags=["media", "audio", "tts"]
)
def text_to_speech(
    text: str,
    voice: str = "Kore",
    model: str = "flash",
    speakers: Optional[List[Dict[str, str]]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generate speech from text using Gemini TTS.
    Supports single-speaker and multi-speaker (up to 2) audio generation.
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
