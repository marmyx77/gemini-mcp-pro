# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-12-08

### Added
- `gemini_analyze_image`: New tool for image analysis using Gemini vision capabilities
  - Supports PNG, JPG, JPEG, GIF, WEBP formats
  - Use cases: describe images, extract text (OCR), identify objects, answer questions
  - Default model: Gemini 2.5 Flash (reliable vision)
  - Optional: Gemini 3 Pro (experimental)

## [1.0.0] - 2025-12-08

### Added
- Initial release with 11 tools across 3 categories

#### Text & Reasoning
- `ask_gemini`: Text generation with optional thinking mode
- `gemini_code_review`: Code analysis with security, performance, and quality focus
- `gemini_brainstorm`: Creative ideation and problem-solving

#### Web & Knowledge
- `gemini_web_search`: Real-time search with Google grounding and citations
- `gemini_file_search`: RAG queries on uploaded documents
- `gemini_create_file_store`: Create document stores for RAG
- `gemini_upload_file`: Upload files to stores (PDF, DOCX, code, etc.)
- `gemini_list_file_stores`: List available document stores

#### Multi-Modal Generation
- `gemini_generate_image`: Native image generation (up to 4K with Gemini 3 Pro)
- `gemini_generate_video`: Video generation with Veo 3.1 (720p/1080p, native audio)
- `gemini_text_to_speech`: TTS with 30 voices, single and multi-speaker support
