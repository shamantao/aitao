# OnlyOffice AI + AItao (Local RAG) Integration Guide

This guide provides a simple and reproducible setup for one local user (MVP).

Goal:
- Use the OnlyOffice chat/prompt UI as the frontend.
- Use AItao as the OpenAI-compatible backend.
- Keep AItao RAG enabled so answers use your local indexed context.

---

## 1) Architecture (MVP)

OnlyOffice AI client -> OpenAI-compatible API -> AItao -> Ollama + RAG context

Important:
- You do not need an MCP server for this MVP.
- AItao already exposes:
  - `POST /v1/chat/completions`
  - `GET /v1/models`

---

## 2) Prerequisites

- AItao installed and configured.
- Ollama installed.
- At least one Ollama model pulled.
- Your document folders configured in `config/config.yaml` under `indexing.include_paths`.

Recommended checks:

```bash
# From AItao project root
./aitao.sh models status
./aitao.sh config validate
```

---

## 3) Start AItao services

From the AItao project root:

```bash
# Start all core services (Meilisearch, API, worker)
./aitao.sh start

# Optional: verify API specifically
./aitao.sh api status
```

If Ollama is not running:

```bash
ollama serve
```

---

## 4) Build the RAG context (mandatory)

If your files were never indexed, run:

```bash
./aitao.sh scan run
./aitao.sh queue status
```

Wait until indexing is complete (queue mostly empty) before testing OnlyOffice.

---

## 5) Validate API endpoints before OnlyOffice

Use these exact checks:

```bash
# Health
curl -s http://127.0.0.1:8200/api/health

# OpenAI-compatible models
curl -s http://127.0.0.1:8200/v1/models

# OpenAI-compatible chat
curl -s http://127.0.0.1:8200/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-local" \
  -d '{
    "model": "llama3.1-context",
    "messages": [{"role": "user", "content": "Say hello in one sentence."}],
    "stream": false
  }'
```

If this works in terminal, OnlyOffice can work with the same values.

---

## 6) Configure OnlyOffice AI client

In OnlyOffice Desktop AI settings (Plugins → AI Assistant → ⚙️ → Add AI Model):

| Field | Value | Notes |
|---|---|---|
| Provider | `OpenAI` | Select from the dropdown |
| URL | `http://127.0.0.1:8200` | **No `/v1`** — the plugin adds it automatically |
| API Key | `sk-local` | **Must start with `sk-`** — any value like `sk-local` works |
| Model | `llama3.1-context` | Exact ID from `/v1/models` |

**Critical rules** (source of all 3 common error messages):
1. URL must NOT contain `/v1` — the OpenAI plugin adds `/v1` itself
2. URL must use `127.0.0.1`, NOT `localhost` (macOS resolves localhost → IPv6)
3. API key must start with `sk-` — OnlyOffice's native layer validates this format

Recommended model IDs for AItao RAG behavior:
- `llama3.1-context` (RAG enabled, good default)
- `llama3.1-basic` (no RAG, for comparison)
- `qwen-coder-context` (RAG + code-oriented model)

Note:
- Model names must match exactly what `/v1/models` returns.

---

## 7) Quick RAG verification from OnlyOffice

Use a prompt that references your private corpus:

1. Ask a question about a known internal document (title/date/keyword).
2. Ask the same question with:
   - `llama3.1-basic` (expected weaker context)
   - `llama3.1-context` (expected context-aware answer)

If `-context` clearly performs better, the AItao RAG path is active.

---

## 8) Troubleshooting: the 3 OnlyOffice error messages

All 3 messages come from OnlyOffice's **native C++ layer** (not from AItao).

---

### "invalid URL" (URL invalide)

**Seen when**: using the Ollama provider with `/v1` in the URL  
**Cause**: the plugin already has `addon = "v1"` — it appends `/v1` to the URL.  
Putting `/v1` in the URL results in `/v1/v1/models` → invalid.  
**Fix**: use `http://127.0.0.1:11434` (no `/v1`)  
**Same rule for OpenAI provider pointing to AItao**: use `http://127.0.0.1:8200` (no `/v1`)

---

### "Fournisseur indisponible" (Provider unavailable)

Two possible causes:

**Cause A — empty API key**: OnlyOffice's native layer requires a non-empty key  
for the OpenAI provider. Even though AItao does not check keys,  
OnlyOffice rejects the empty string before making the request.  
**Fix**: enter `sk-local` as the key (anything starting with `sk-`)

**Cause B — wrong address**: `localhost` on macOS resolves to `::1` (IPv6).  
AItao listens on IPv4 (`0.0.0.0`), so `localhost:8200` gets  
connection refused.  
**Fix**: always use `http://127.0.0.1:8200` (explicit IPv4)

---

### "invalid API Key" (Clé API invalide)

**Cause**: OnlyOffice's native layer validates that OpenAI keys start with `sk-`.  
Keys like `api1234567890` or any non-`sk-` value are rejected.  
**Fix**: use `sk-local` (or any value starting with `sk-`)

---

### General connection check

```bash
curl http://127.0.0.1:8200/v1/models
```
If this returns JSON, AItao is reachable and the URL is correct.

### Model not found

- Copy the model ID exactly from `/v1/models`
- Check Ollama model availability: `./aitao.sh models status`

### Answers ignore your context

- Ensure documents are indexed: `./aitao.sh scan run`
- Check queue progress: `./aitao.sh queue status`
- Use a `-context` model instead of `-basic`

### Port conflict on 8200

- Change `api.port` in `config/config.yaml`
- Then use the same new port in OnlyOffice base URL

---

## 9) Reproducible onboarding checklist (for any user)

Run in order:

1. `./aitao.sh start`
2. `./aitao.sh scan run`
3. `./aitao.sh queue status`
4. `curl http://127.0.0.1:8200/v1/models`
5. Configure OnlyOffice with `openai` + `http://127.0.0.1:8200/v1`
6. Select `llama3.1-context`
7. Ask a corpus-specific question and validate answer quality

This sequence is the MVP reference procedure for local, single-user deployment.