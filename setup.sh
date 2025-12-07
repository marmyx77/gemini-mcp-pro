#!/bin/bash
# gemini-mcp-pro Setup Script v1.0.0
# Installs and configures the Gemini MCP server for Claude Code

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  gemini-mcp-pro Setup v1.0.0               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Check if API key was provided
API_KEY="$1"
if [ -z "$API_KEY" ]; then
    echo -e "${RED}Error: Please provide your Gemini API key${NC}"
    echo ""
    echo "Usage: ./setup.sh YOUR_GEMINI_API_KEY"
    echo ""
    echo "Get a free API key at: https://aistudio.google.com/apikey"
    exit 1
fi

# Validate API key format (basic check)
if [[ ! "$API_KEY" =~ ^AIza ]]; then
    echo -e "${YELLOW}Warning: API key doesn't match expected format (AIza...)${NC}"
    echo "Continuing anyway..."
    echo ""
fi

# Check Python version
echo "Checking requirements..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed.${NC}"
    echo "Install Python 3.8+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo -e "${RED}Error: Python 3.8+ required, found $PYTHON_VERSION${NC}"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Python $PYTHON_VERSION"

# Check Claude Code CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}Error: Claude Code CLI not found${NC}"
    echo "Install with: npm install -g @anthropic-ai/claude-code"
    exit 1
fi
echo -e "  ${GREEN}✓${NC} Claude Code CLI"

# Create MCP server directory
echo ""
echo "Installing server..."
mkdir -p ~/.claude-mcp-servers/gemini-mcp-pro

# Copy server file
cp server.py ~/.claude-mcp-servers/gemini-mcp-pro/
echo -e "  ${GREEN}✓${NC} Server installed to ~/.claude-mcp-servers/gemini-mcp-pro/"

# Install Python dependencies
echo ""
echo "Installing dependencies..."
pip3 install --quiet --user google-genai 2>/dev/null || \
pip3 install --quiet --break-system-packages google-genai 2>/dev/null || \
pip3 install --quiet google-genai
echo -e "  ${GREEN}✓${NC} google-genai SDK installed"

# Remove any existing MCP configuration
echo ""
echo "Configuring Claude Code..."
claude mcp remove gemini-mcp-pro 2>/dev/null || true

# Add MCP server with environment variable for API key
claude mcp add gemini-mcp-pro --scope user -e GEMINI_API_KEY="$API_KEY" \
    -- python3 ~/.claude-mcp-servers/gemini-mcp-pro/server.py

echo -e "  ${GREEN}✓${NC} MCP server registered"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  Setup Complete!                           ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code (exit and reopen)"
echo "  2. Verify with: claude mcp list"
echo ""
echo "Available tools (11 total):"
echo "  • ask_gemini          - Questions with thinking mode"
echo "  • gemini_code_review  - Code analysis"
echo "  • gemini_brainstorm   - Creative ideation"
echo "  • gemini_web_search   - Real-time search with citations"
echo "  • gemini_file_search  - RAG document queries"
echo "  • gemini_create_file_store"
echo "  • gemini_upload_file"
echo "  • gemini_list_file_stores"
echo "  • gemini_generate_image - Up to 4K images"
echo "  • gemini_generate_video - Veo 3.1 with audio"
echo "  • gemini_text_to_speech - 30 natural voices"
echo ""
echo "Documentation: https://github.com/marmyx77/gemini-mcp-pro"
echo ""
