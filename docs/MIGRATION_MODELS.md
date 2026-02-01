# Model Migration Guide: GGUF → Ollama

**Version:** 2.3.21.5  
**Date:** February 2026  
**Status:** Current recommended approach

---

## Overview

AItao V2 has migrated from local GGUF model management to **Ollama** as the primary LLM backend. This guide explains the transition and helps you clean up legacy files.

## Why Ollama?

| Aspect | GGUF (V1) | Ollama (V2) |
|--------|-----------|-------------|
| **Model management** | Manual download & path config | Automatic via `ollama pull` |
| **Updates** | Manual re-download | `ollama pull model:tag` |
| **GPU optimization** | Manual llama.cpp config | Automatic detection |
| **Memory management** | User-managed | Auto hot-swap by Ollama |
| **Multi-model** | Complex setup | Native support |

## What Changed

### Before (V1 - GGUF)
```yaml
# Old config.yaml
llm:
  models_dir: "/path/to/gguf_models"
  default_model: "llama-3.1-8b-instruct-q4_k_m.gguf"
```

### After (V2 - Ollama)
```yaml
# New config.yaml
llm:
  ollama:
    host: "http://localhost:11434"
    default_model: "llama3.1-local:latest"
  models:
    - name: llama3.1-local:latest
      required: true
      roles: [chat, rag]
```

## Migration Steps

### 1. Verify Ollama is Working

```bash
# Check Ollama is running
./aitao.sh status

# List installed models
ollama list

# Verify configured models are present
./aitao.sh models status
```

### 2. Confirm Data Integrity

Before deleting GGUF files, ensure your Ollama models work:

```bash
# Test a query
./aitao.sh search "test query"

# Or via API
curl http://localhost:8765/api/health
```

### 3. Remove Legacy GGUF Files (Optional)

If you're satisfied with Ollama, you can reclaim disk space:

```bash
# Check current GGUF storage (if any)
ls -lh ~/Downloads/_sources/aitao/models/

# Typical GGUF sizes:
# - llama-3.1-8b-q4_k_m.gguf: ~4.6 GB
# - qwen2.5-coder-7b-q4_k_m.gguf: ~4.4 GB
# - Total potential savings: 10-20 GB
```

⚠️ **Keep GGUF files if:**
- You have custom fine-tuned models
- You need offline access without Ollama
- You're testing specific quantization variants

### 4. Update config.yaml

Remove legacy `models_dir` if present:

```yaml
# Remove this section (no longer needed):
# llm:
#   models_dir: "/path/to/gguf_models"
```

## Model Mapping Reference

| Legacy GGUF | Ollama Equivalent | Command |
|-------------|-------------------|---------|
| `llama-3.1-8b-instruct-q4_k_m.gguf` | `llama3.1:8b` | `ollama pull llama3.1:8b` |
| `qwen2.5-coder-7b-q4_k_m.gguf` | `qwen2.5-coder:7b` | `ollama pull qwen2.5-coder:7b` |
| `mistral-7b-instruct-q4_k_m.gguf` | `mistral:7b` | `ollama pull mistral:7b` |
| `codellama-13b-q4_k_m.gguf` | `codellama:13b` | `ollama pull codellama:13b` |

## Custom/Fine-tuned Models

If you have custom GGUF models, you can import them into Ollama:

```bash
# Create a Modelfile
cat > Modelfile << 'EOF'
FROM /path/to/your-custom-model.gguf
PARAMETER temperature 0.7
SYSTEM "You are a helpful assistant."
EOF

# Import into Ollama
ollama create my-custom-model -f Modelfile

# Verify
ollama list
```

## CLI Model Management

AItao V2 provides CLI commands for model management:

```bash
# Check model status
./aitao.sh models status

# Add a new model
./aitao.sh models add mistral:7b --role rag

# Remove a model
./aitao.sh models remove mistral:7b --force

# Download missing models
./aitao.sh models pull
```

## Troubleshooting

### Ollama not running
```bash
# Start Ollama
ollama serve &

# Or via system service (macOS)
brew services start ollama
```

### Model not found
```bash
# List available models
ollama list

# Pull missing model
ollama pull llama3.1:8b
```

### Memory issues
Ollama auto-manages memory, but you can:
```bash
# Unload all models (free VRAM)
ollama stop

# Check resource usage
./aitao.sh status
```

## Summary

1. ✅ Ollama is now the standard backend
2. ✅ No manual GGUF management needed
3. ✅ Use `./aitao.sh models` commands
4. ✅ Legacy GGUF files can be deleted (optional)
5. ✅ Custom models can be imported via Modelfile

---

**Questions?** Check `./aitao.sh --help` or open an issue on GitHub.
