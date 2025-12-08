# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.1.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |

## API Key Security

### Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables**:
   ```bash
   export GEMINI_API_KEY="your-key-here"
   ```
3. **Use Claude Code's `-e` flag** when registering:
   ```bash
   claude mcp add --scope user gemini-collab \
     -e GEMINI_API_KEY=YOUR_KEY \
     python3 ~/.claude-mcp-servers/gemini-collab/server.py
   ```

### What NOT to Do

- Don't paste API keys in `claude_desktop_config.json` if you share configs
- Don't hardcode keys in `server.py`
- Don't commit `.env` files with real keys

## Data Privacy

### What Data is Sent to Google

When using this MCP server, the following data is sent to Google's Gemini API:

- **Text prompts** for ask_gemini, code_review, brainstorm, web_search
- **Code snippets** for code_review
- **Documents** uploaded to File Search stores
- **Images** for gemini_analyze_image (vision analysis)
- **Image/Video prompts** for generation tools
- **Text** for text-to-speech conversion

### Data Retention

- Refer to [Google AI's privacy policy](https://ai.google.dev/gemini-api/terms)
- File Search stores persist on Google's servers until deleted
- Generated images/videos are temporarily stored during generation

### Sensitive Data

**Do not send:**
- Passwords or credentials
- Private keys or tokens
- Personal identifiable information (PII)
- Confidential business data
- Healthcare/financial data subject to regulations

## Reporting Vulnerabilities

### How to Report

1. **Do NOT** open a public issue for security vulnerabilities
2. Email the maintainer directly (see repository owner)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 1 week
- **Fix timeline**: Depends on severity

### Severity Levels

| Level | Description | Response |
|-------|-------------|----------|
| Critical | API key exposure, RCE | Immediate fix |
| High | Data leakage, auth bypass | Fix within 1 week |
| Medium | Logic errors, DoS | Fix within 1 month |
| Low | Minor issues | Next release |

## Security Features

### Input Validation

- File paths are validated before file operations
- API key presence is verified at startup
- Invalid tool parameters return errors, not crashes

### Error Handling

- Exceptions are caught and return user-friendly messages
- Stack traces are not exposed to end users
- Sensitive data is not included in error messages

## Known Limitations

1. **No encryption at rest**: Files uploaded to RAG stores are stored on Google's servers
2. **No access control**: Anyone with access to Claude Code can use the MCP tools
3. **API key visibility**: The key is visible to processes that can read environment variables

## Security Updates

Watch the repository for security-related releases. Update promptly when security patches are released:

```bash
git pull origin main
./setup.sh YOUR_API_KEY
```
