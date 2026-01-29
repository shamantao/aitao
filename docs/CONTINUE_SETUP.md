# Continue.dev Setup Guide for AItao

This guide explains how to configure [Continue.dev](https://continue.dev) to use AItao as your AI backend, enabling RAG-enhanced coding assistance with local LLMs.

## Overview

AItao provides OpenAI-compatible endpoints that Continue.dev can use:
- `/v1/chat/completions` - Chat with RAG context
- `/v1/models` - List available models

This means Continue.dev will automatically benefit from RAG context enrichment when asking questions about your codebase.

## Prerequisites

1. **AItao running**: Ensure the AItao API server is running
   ```bash
   ./aitao.sh start
   ```

2. **Ollama running**: AItao requires Ollama as the LLM backend
   ```bash
   ollama serve
   ```

3. **Models available**: At least one model should be installed in Ollama
   ```bash
   ollama list
   ```

## Configuration

### Option 1: Using config.yaml (Recommended)

Edit `~/.continue/config.yaml`:

```yaml
name: AItao Local RAG
version: 1.0.0
schema: v1

models:
  # Primary chat model with RAG
  - name: AItao Qwen Coder
    provider: openai
    model: qwen2.5-coder:7b
    apiBase: "http://localhost:5000/v1"
    apiKey: "sk-aitao-local"  # Any non-empty value works
    roles:
      - chat
      - edit
      - apply

  # Alternative model
  - name: AItao Llama 3.1
    provider: openai
    model: llama3.1:8b
    apiBase: "http://localhost:5000/v1"
    apiKey: "sk-aitao-local"
    roles:
      - chat

  # Autocomplete (can use same or different model)
  - name: Autocomplete
    provider: openai
    model: qwen2.5-coder:7b
    apiBase: "http://localhost:5000/v1"
    apiKey: "sk-aitao-local"
    roles:
      - autocomplete

# Context providers (built-in)
context:
  - provider: code
  - provider: docs
  - provider: diff
  - provider: terminal
  - provider: problems
  - provider: folder
  - provider: codebase
```

### Option 2: Using config.json (Legacy)

Edit `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "AItao Qwen Coder (RAG)",
      "provider": "openai",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:5000/v1",
      "apiKey": "sk-aitao-local"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Autocomplete",
    "provider": "openai",
    "model": "qwen2.5-coder:7b",
    "apiBase": "http://localhost:5000/v1",
    "apiKey": "sk-aitao-local"
  }
}
```

## API Port Configuration

By default, AItao runs on port `5000`. If you need to use a different port, update both:

1. **AItao config** (`config/config.toml`):
   ```toml
   [api]
   port = 5000
   ```

2. **Continue.dev config**: Update `apiBase` to match

## Verifying the Setup

### 1. Check AItao is running

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{"status": "healthy", "version": "2.3.19", ...}
```

### 2. Check models are available

```bash
curl http://localhost:5000/v1/models
```

Expected response:
```json
{
  "object": "list",
  "data": [
    {"id": "qwen2.5-coder:7b", "object": "model", ...},
    {"id": "llama3.1:8b", "object": "model", ...}
  ]
}
```

### 3. Test chat endpoint

```bash
curl -X POST http://localhost:5000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:7b",
    "messages": [{"role": "user", "content": "Hello"}],
    "stream": false
  }'
```

### 4. Test in Continue.dev

1. Open VS Code with Continue extension
2. Open the Continue sidebar (Cmd+L / Ctrl+L)
3. Select your AItao model from the dropdown
4. Ask a question about your code

## RAG Features

When using AItao through Continue.dev, your prompts are automatically enriched with relevant context from your indexed documents:

- **Code snippets** from your workspace
- **Documentation** you've indexed
- **Previous conversations** (if enabled)

### Controlling RAG

You can control RAG behavior in your requests:

```json
{
  "model": "qwen2.5-coder:7b",
  "messages": [...],
  "rag_enabled": true,  // Enable/disable RAG (default: true)
}
```

The response includes metadata about which documents were used:

```json
{
  "choices": [...],
  "rag_context": [
    {"id": "doc1", "path": "/src/utils.py", "score": 0.95},
    {"id": "doc2", "path": "/README.md", "score": 0.87}
  ]
}
```

## Troubleshooting

### "Connection refused" error

1. Check AItao is running: `curl http://localhost:5000/api/health`
2. Check the port in config matches
3. Check firewall settings

### "Model not found" error

1. Verify model is installed: `ollama list`
2. Check model name matches exactly (including tag, e.g., `:7b`)

### Slow responses

1. Check Ollama resource usage
2. Consider using a smaller quantized model
3. Reduce `max_context_docs` in AItao config

### RAG context not appearing

1. Ensure documents are indexed: `curl http://localhost:5000/api/stats`
2. Check RAG is enabled in config
3. Verify search is working: `curl -X POST http://localhost:5000/api/search -d '{"query": "test"}'`

## Advanced Configuration

### Custom System Prompt

Edit `config/system_prompt.txt` to customize the AI's behavior.

### RAG Settings

In `config/config.toml`:

```toml
[rag]
max_context_docs = 5          # Max documents to include
context_max_tokens = 2000     # Max tokens for context
min_relevance_score = 0.3     # Minimum similarity score
```

### Model Settings

```toml
[llm.ollama]
base_url = "http://localhost:11434"
default_model = "qwen2.5-coder:7b"
timeout = 120
```

## Support

- **AItao Issues**: Check logs in `logs/` directory
- **Continue.dev Issues**: See [Continue.dev docs](https://docs.continue.dev)
- **Ollama Issues**: Run `ollama logs`
