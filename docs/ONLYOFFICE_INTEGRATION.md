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

In OnlyOffice AI settings:

- Provider: `openai`
- Base URL: `http://127.0.0.1:8200/v1`
- API key: `sk-local` (any non-empty value)
- Model: one model ID returned by `/v1/models`

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

## 8) Troubleshooting (most common)

### OnlyOffice says "provider unavailable" / "fournisseur indisponible"

**Root cause on macOS**: `localhost` resolves to `::1` (IPv6) by default.
AItao by default only listens on IPv4. OnlyOffice's embedded Chromium tries IPv6
first → connection refused → "provider unavailable".

**Immediate fix**: always use `http://127.0.0.1:8200` (explicit IPv4), **never**
`http://localhost:8200`.

**Permanent fix**: edit `config/config.yaml`:
```yaml
api:
  host: "::"   # dual-stack IPv4+IPv6 (macOS/Linux)
```
Restart AItao after this change. Both `localhost` and `127.0.0.1` will then work.

### OnlyOffice says connection failed (general)

- Verify API is running: `./aitao.sh api status`
- Verify endpoint: `curl http://127.0.0.1:8200/v1/models`
- Ensure base URL includes `/v1`
- Ensure API key is non-empty in OnlyOffice

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