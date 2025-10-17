# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development Commands

### Setup and Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python src/main.py
```

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_agent.py

# Run with async support and verbose output
python -m pytest tests/ -v --asyncio-mode=auto
```

### Code Quality
```bash
# Code formatting
black src/ tests/

# Linting
flake8 src/ tests/

# Type checking
mypy src/
```

## Architecture Overview

### Core Components

**EmailAgent (`src/email_agent/agent.py`)**
- Main orchestrator that runs the email processing loop
- Manages email fetching, AI analysis, rule application, and action execution
- Handles async processing with configurable batch sizes and intervals
- Maintains state of processed emails to avoid duplicates

**EmailClient (`src/email_agent/email_client.py`)**
- Handles IMAP/SMTP operations for reading and sending emails
- Supports SSL/TLS connections and multiple email providers
- Parses raw email data into structured EmailMessage objects
- Manages connection lifecycle and error handling

**AIProcessor (`src/email_agent/ai_processor.py`)**
- Integrates with OpenAI and Anthropic APIs for email analysis
- Classifies emails by category, sentiment, priority, and response requirements
- Generates AI-powered responses based on email content and context
- Returns structured EmailAnalysis objects with confidence scores

**Config (`src/email_agent/config.py`)**
- Pydantic-based configuration management with YAML file support
- Environment variable substitution for sensitive data
- Structured config sections: email, AI, agent behavior, processing rules, logging

### Processing Flow

1. **Email Fetching**: Agent connects to IMAP server and fetches unread emails in batches
2. **AI Analysis**: Each email is analyzed for category, priority, sentiment, and action requirements
3. **Rule Matching**: Email content and analysis are matched against configured processing rules
4. **Action Execution**: Rules trigger actions like archiving, forwarding, auto-replies, or notifications
5. **Response Generation**: For emails requiring responses, AI generates contextual replies
6. **State Management**: Processed emails are tracked to prevent duplicate processing

### Configuration Structure

The agent is configured via `config/config.yaml` with sections for:
- **Email Provider**: IMAP/SMTP settings, credentials, SSL configuration
- **AI Models**: Provider selection (OpenAI/Anthropic), model parameters, API keys
- **Agent Behavior**: Processing intervals, batch sizes, auto-reply settings
- **Processing Rules**: Condition-based email routing with actions
- **Logging**: Level, file output, rotation settings

### Rule-Based Processing

Rules define conditions (subject keywords, sender domains, categories) and actions:
- **Archive/Mark Read**: Automatically process newsletters or notifications
- **Forward**: Route urgent emails to managers or support teams
- **Notify**: Generate high-priority alerts for critical emails
- **Auto-reply**: Send templated responses for common inquiries

### Testing Strategy

Tests use pytest with asyncio support and extensive mocking:
- **Unit Tests**: Individual component functionality and edge cases
- **Integration Tests**: Email processing workflows and rule execution  
- **Mock Objects**: AI API calls, email server connections, and external dependencies
- **Async Testing**: Proper handling of async/await patterns throughout

### Key Dependencies

- **Email**: `imaplib2`, `email-validator` for email protocol handling
- **AI**: `openai`, `anthropic`, `langchain` for intelligent processing
- **Config**: `pydantic`, `pyyaml` for structured configuration
- **Async**: `asyncio`, `aiohttp` for concurrent operations
- **Testing**: `pytest-asyncio`, `pytest-mock` for async test support

## Development Notes

### Adding New Email Providers
Extend `EmailClient` class with provider-specific IMAP/SMTP configurations. Update `EmailConfig` to include new provider settings.

### Adding New AI Providers
Implement new methods in `AIProcessor` following the pattern of `_analyze_with_*` and `_generate_with_*` methods. Update the `_setup_client` method for provider initialization.

### Extending Processing Rules
Add new condition types in `_rule_matches` method and new action types in `_execute_rule_actions` method of `EmailAgent` class.

### Environment Variables
Use `${VARIABLE_NAME}` syntax in config.yaml for sensitive values like API keys and passwords. The config loader automatically substitutes environment variables.

### Logging
All components use structured logging via Python's logging module. Log files are rotated based on size limits defined in configuration.