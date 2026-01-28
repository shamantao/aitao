"""
Indexation pipeline for AItao V2.

Modules:
- scanner: Filesystem scanner (FSEvents)
- queue: JSON task queue
- worker: Background worker daemon
- indexer: Document indexer orchestrator
- text_extractor: Direct text extraction (PDF, DOCX)
- categorizer: Auto-categorization (LLM)
"""
