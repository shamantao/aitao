# LLM Models Documentation

This document explains how AiTao manages LLM models via Ollama and how to diagnose/fix common issues.

## Virtual Models (US-029b)

AiTao exposes **virtual models** via its OpenAI-compatible API, allowing you to control RAG behavior through model names.

### Available Suffixes

Each real model (e.g., `qwen2.5-coder-local:latest`) is exposed with **2 suffixes**:

| Suffix | Behavior | Use Case | Speed |
|--------|----------|----------|-------|
| `-basic` | No RAG context | Fast responses for general questions | ⚡ Fast |
| `-context` | Full RAG with documents | Precise answers from your documents | 🐢 Slower |

### Example

When connecting to AiTao API (e.g., from Open WebUI):

```
Available models in dropdown:
✅ llama3.1-basic          → Fast chat without documents
✅ llama3.1-context        → Chat with access to your documents
✅ qwen-coder-basic        → Fast code help
✅ qwen-coder-context      → Code help with your project docs
✅ qwen-vl-basic           → Vision without documents (OCR)
✅ qwen-vl-context         → Vision with document analysis
```

### Why 2 Suffixes?

- **User Control:** You decide when to use RAG (it's slower but more accurate)
- **Simplicity:** Only 2 clear choices instead of 4+ confusing options
- **Performance:** `-basic` is 2-3x faster for simple questions

### Total Models Exposed

With 3 base models × 2 suffixes = **6 virtual models** + 3 real models = **9 models total**

This is a **40% reduction** from the previous 15 models.

---

## Quick Reference

```bash
# Check model status
./aitao.sh models status

# Check for template issues
./aitao.sh models check

# Fix broken templates
./aitao.sh models fix

# Validate models with a test prompt
./aitao.sh models validate

# Download missing models
./aitao.sh models pull
```

## Model Templates

### What is a Template?

Ollama models require a **template** to structure conversations. The template defines how user messages, system prompts, and assistant responses are formatted.

Different model families use different template formats:

| Model Family | Template Format | Key Tokens |
|--------------|-----------------|------------|
| Qwen (2.5, 3) | ChatML | `<\|im_start\|>`, `<\|im_end\|>` |
| Llama 3.x | Llama | `<\|start_header_id\|>`, `<\|eot_id\|>` |
| Mistral | Mistral | `[INST]`, `[/INST]` |

### Common Template Problems

#### Problem: Model responds with gibberish or hallucinations

**Symptom:** The model gives incoherent responses, repeats tokens, or hallucinates.

**Cause:** Broken or missing template. This often happens when:
1. You import a GGUF file manually without providing the correct Modelfile
2. You use `ollama create` with an incomplete template

**Diagnosis:**
```bash
# Check the model's template
ollama show qwen2.5-coder-local --modelfile

# If you see just "TEMPLATE {{ .Prompt }}" - the template is broken!
```

**Fix:**
```bash
./aitao.sh models fix qwen2.5-coder-local
```

### Template Examples

#### Correct Qwen ChatML Template

```
TEMPLATE """{{- if .System }}
<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}
{{- range .Messages }}
<|im_start|>{{ .Role }}
{{ .Content }}<|im_end|>
{{ end }}
<|im_start|>assistant
"""
```

#### Broken Template (BAD)

```
TEMPLATE {{ .Prompt }}
```

This minimal template doesn't provide any conversation structure, causing the model to behave unpredictably.

## Installing Models

### From Ollama Hub (Recommended)

```bash
# Pull official models
ollama pull qwen2.5-coder:7b
ollama pull llama3.1:8b

# Add to AiTao config
./aitao.sh models add qwen2.5-coder:7b --role code --required
```

### From GGUF File (Advanced)

If you have a custom GGUF file, use the safe import command:

```bash
# This automatically applies the correct template
./aitao.sh models import /path/to/model.gguf --name my-model --family qwen
```

**Never** use bare `ollama create` with just a FROM line - always include the full template.

## Model Configuration

Models are configured in `config/config.yaml`:

```yaml
llm:
  default_model: qwen2.5-coder:7b
  models:
    - name: qwen2.5-coder:7b
      required: true
      roles: [code]
      size_gb: 4.7
    - name: llama3.1:8b
      required: false
      roles: [general]
      size_gb: 4.7
```

### Required vs Optional Models

- **Required:** AiTao won't start without these models
- **Optional:** Used if available, but not blocking

## Troubleshooting

### Model not responding

1. Check if Ollama is running: `ollama list`
2. Check template: `ollama show <model> --modelfile`
3. Run fix: `./aitao.sh models fix`

### Model gives wrong language responses

The system prompt may be missing. Check that the template includes the System section:

```
{{- if .System }}
<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}
```

### Model is very slow

1. Check your hardware (Apple Silicon recommended for MLX)
2. Use a smaller quantization (Q4 vs Q8)
3. Reduce context length (`num_ctx` parameter)

## Versioned Modelfiles

AiTao stores correct templates in `config/modelfiles/`:

```
config/modelfiles/
├── qwen2.5-coder.Modelfile    # Qwen ChatML template
├── qwen3-vl.Modelfile         # Qwen Vision-Language
└── llama3.1.Modelfile         # Llama template
```

These are tracked in Git and used by `./aitao.sh models fix` to repair broken templates.

## Health Checks

### Startup Validation

When AiTao starts, it automatically:
1. Checks if required models are installed
2. Validates templates for common issues
3. Reports any problems in the startup log

### API Health Check

```bash
curl http://localhost:8200/health/models
```

Returns JSON with model status including template health.

## Support

If you encounter model issues not covered here:

1. Run `./aitao.sh models check --json > model_report.json`
2. Check logs in `logs/` directory
3. Open an issue with the model report attached
