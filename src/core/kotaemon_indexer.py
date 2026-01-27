#!/usr/bin/env python3
"""
Lightweight Indexer for AI Tao (LanceDB + sentence-transformers)

Responsibilities:
- Provide a minimal, local-first indexing interface
- Use LanceDB for vector + document storage (performance, memory efficiency)
- Use sentence-transformers for embeddings (all-MiniLM-L6-v2, ~100 MB, fast, multilingual)
- Enforce project conventions: resolve paths via path_manager, centralize logging

Notes:
- No hard-coded absolute paths. All storage roots come from path_manager and config.toml.
- Gracefully degrades if dependencies missing.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Tuple

# Project utilities (English docstrings required)
try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
    from src.core.failed_files_tracker import FailedFilesTracker
except ImportError:
    from core.path_manager import path_manager  # type: ignore
    from core.logger import get_logger  # type: ignore
    from core.failed_files_tracker import FailedFilesTracker  # type: ignore

logger = get_logger("AITaoIndexer", "kotaemon_indexer.log")

# Optional imports – keep module importable without dependencies installed
INDEXER_AVAILABLE = True
try:
    import lancedb
    from sentence_transformers import SentenceTransformer
except Exception as e:  # noqa: BLE001
    INDEXER_AVAILABLE = False
    logger.warning(f"Indexer dependencies missing ({e}). Indexing will be disabled.")

# Optional OCR/inspection deps
try:  # pdf text extraction
    from pdfminer.high_level import extract_text as pdf_extract_text
    PDF_EXTRACT_AVAILABLE = True
except Exception:
    PDF_EXTRACT_AVAILABLE = False

try:  # pdf raster conversion
    from pdf2image import convert_from_path
    PDF2IMG_AVAILABLE = True
except Exception:
    PDF2IMG_AVAILABLE = False

try:  # image ops
    import cv2
    CV_AVAILABLE = True
except Exception:
    CV_AVAILABLE = False

try:  # lightweight OCR
    import easyocr
    EASY_AVAILABLE = True
except Exception:
    EASY_AVAILABLE = False

try:  # vision model for complex OCR
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Llava15ChatHandler
    LLAMA_CPP_AVAILABLE = True
except Exception:
    LLAMA_CPP_AVAILABLE = False

try:  # image encoding
    import base64
    BASE64_AVAILABLE = True
except Exception:
    BASE64_AVAILABLE = False


class AITaoIndexer:
    """Lightweight, local-first indexer using LanceDB + sentence-transformers.

    - Uses `all-MiniLM-L6-v2` for embeddings by default (fast, multilingual, ~100 MB)
    - Stores vectors and documents under the configured storage root via LanceDB
    - No external APIs or cloud dependencies
    """

    def __init__(self, collection_name: str = "default") -> None:
        """Initialize indexer with LanceDB and embeddings.
        
        Args:
            collection_name: Name of the LanceDB collection for this index
        """
        self.collection_name = collection_name
        self.storage_root: Path = path_manager.get_storage_root()
        self.vector_db_path: Path = path_manager.get_vector_db_path()

        self._enabled = INDEXER_AVAILABLE
        self.db = None
        self.table = None
        self.embedding_model = None
        self.failed_tracker = FailedFilesTracker()
        self.ocr_config = (
            path_manager.get_ocr_config()
            if hasattr(path_manager, "get_ocr_config")
            else {
                "engine": "auto",
                "table_area_min": 0.15,
                "min_intersections": 4,
                "min_line_density": 0.0005,
                "qwen_model_path": "",
            }
        )
        self.ocr_reader = None  # lazy init for EasyOCR
        self.qwen_model = None  # lazy init for Qwen-VL

        if not self._enabled:
            logger.warning("Indexer disabled: dependencies not available.")
            return

        try:
            # Initialize LanceDB
            db_dir = str(self.vector_db_path)
            os.makedirs(db_dir, exist_ok=True)
            self.db = lancedb.connect(db_dir)
            
            # Load embedding model (downloads ~100 MB on first use to ~/.cache)
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            
            # Ensure collection exists (will be created on first insert if not exists)
            try:
                self.table = self.db.open_table(collection_name)
                logger.info(f"✅ Opened existing collection: {collection_name}")
                self._ensure_schema()
            except Exception:
                # Table doesn't exist yet; will be created on first insert
                logger.info(f"📝 Collection '{collection_name}' will be created on first index")
                self.table = None
            
            logger.info(
                f"✅ Indexer initialized | collection={collection_name} | db_path={self.vector_db_path}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize indexer: {e}")
            self._enabled = False

    def is_enabled(self) -> bool:
        """Return True if indexer is ready to index files."""
        return self._enabled and self.embedding_model is not None

    def index_files(self, file_paths: Iterable[Path | str]) -> int:
        """Index a batch of files.

        Args:
            file_paths: Iterable of file paths (str or Path)

        Returns:
            Number of successfully indexed files
        """
        if not self.is_enabled():
            logger.warning("Indexing skipped: indexer not initialized.")
            return 0

        count = 0
        documents = []

        for p in file_paths:
            fp = Path(p)
            if not fp.exists() or not fp.is_file():
                logger.debug(f"⏭️ Skip non-file or missing: {fp}")
                continue

            try:
                suffix = fp.suffix.lower()

                if suffix in {".txt", ".md", ".html", ".json", ".csv", ".log"}:
                    content = self._read_text_file(fp)
                    ocr_used = "none"
                elif suffix == ".pdf":
                    content, ocr_used = self._extract_pdf(fp)
                elif suffix in {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}:
                    content, ocr_used = self._ocr_image(fp)
                else:
                    logger.debug(f"⏭️ Unsupported extension: {fp}")
                    continue

                if not content or not content.strip():
                    logger.debug(f"⏭️ Skip empty content: {fp}")
                    self.failed_tracker.add_failed_file(str(fp), "Empty content", "empty")
                    continue

                embedding = self.embedding_model.encode(content[:500]).tolist()

                doc = {
                    "id": str(fp),
                    "path": str(fp),
                    "filename": fp.name,
                    "content": content,
                    "embedding": embedding,
                    "size_bytes": fp.stat().st_size,
                    "ocr_engine": ocr_used,
                }
                documents.append(doc)
                count += 1

                self.failed_tracker.mark_success(str(fp))

            except UnicodeDecodeError as e:
                logger.error(f"❌ Encoding error {fp}: {e}")
                self.failed_tracker.add_failed_file(str(fp), str(e), "encoding")
            except Exception as e:  # noqa: BLE001
                logger.error(f"❌ Failed to index {fp}: {e}")
                self.failed_tracker.add_failed_file(str(fp), str(e), "parse_error")

        # Batch insert into LanceDB
        if documents:
            try:
                if self.table is None:
                    # Create table on first insert
                    self.table = self.db.create_table(self.collection_name, data=documents, mode="overwrite")
                    logger.info(f"✅ Created collection '{self.collection_name}'")
                else:
                    # Append to existing table
                    self.table.add(documents)
                
                logger.info(f"✅ Indexed {count} file(s) into '{self.collection_name}'")
            except Exception as e:
                logger.error(f"❌ Failed to insert documents into LanceDB: {e}")
                return 0

        return count

    # --- Helpers -----------------------------------------------------

    def _read_text_file(self, fp: Path) -> str:
        """Read a text file safely."""
        with open(fp, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _extract_pdf(self, fp: Path) -> Tuple[str, str]:
        """Extract text from PDF using pdfminer; placeholder for raster OCR."""
        if PDF_EXTRACT_AVAILABLE:
            try:
                text = pdf_extract_text(str(fp)) or ""
                if text.strip():
                    return text, "pdf_text"
            except Exception as e:  # noqa: BLE001
                logger.warning(f"PDF text extraction failed {fp}: {e}")
        # Raster OCR fallback for scanned PDFs
        if PDF2IMG_AVAILABLE:
            try:
                images = convert_from_path(str(fp), fmt="png")
                texts: list[str] = []
                for img in images:
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                        img.save(tmp.name, format="PNG")
                        img_text, _ = self._ocr_image(Path(tmp.name))
                        if img_text:
                            texts.append(img_text)
                if texts:
                    return "\n\n".join(texts), "pdf_raster"
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Raster PDF OCR failed {fp}: {e}")

        self.failed_tracker.add_failed_file(str(fp), "PDF appears scanned; raster OCR not available", "pdf_scanned")
        return "", "none"

    def _load_easy_reader(self) -> None:
        """Lazily instantiate EasyOCR reader."""
        if self.ocr_reader is None and EASY_AVAILABLE:
            try:
                self.ocr_reader = easyocr.Reader(["en", "fr", "zh-cn", "zh-tw"], gpu=False)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"EasyOCR init failed: {e}")
                self.ocr_reader = None

    def _ocr_image(self, fp: Path) -> Tuple[str, str]:
        """Route OCR for an image file."""
        engine = self._choose_engine(fp)

        if engine == "easyocr":
            text = self._ocr_image_easy(fp)
            return text, "easyocr"

        if engine == "qwen":
            text = self._ocr_image_qwen(fp)
            if text:  # Success
                return text, "qwen-vl"
            # Fallback to EasyOCR if Qwen fails
            logger.warning(f"Qwen-VL failed for {fp}, falling back to EasyOCR")
            text = self._ocr_image_easy(fp)
            return text, "qwen-fallback-easyocr"

        text = self._ocr_image_easy(fp)
        return text, "easyocr"

    def _ocr_image_easy(self, fp: Path) -> str:
        """Run EasyOCR on an image; returns concatenated text."""
        if not EASY_AVAILABLE:
            self.failed_tracker.add_failed_file(str(fp), "EasyOCR not installed", "ocr_missing")
            return ""

        self._load_easy_reader()
        if self.ocr_reader is None:
            self.failed_tracker.add_failed_file(str(fp), "EasyOCR init failed", "ocr_init")
            return ""

        try:
            results = self.ocr_reader.readtext(str(fp), detail=0, paragraph=True)
            return "\n".join(results)
        except Exception as e:  # noqa: BLE001
            logger.error(f"OCR Easy failed {fp}: {e}")
            self.failed_tracker.add_failed_file(str(fp), str(e), "ocr_easy")
            return ""

    def _load_qwen_model(self) -> None:
        """Lazily instantiate Qwen-VL model."""
        if self.qwen_model is None and LLAMA_CPP_AVAILABLE:
            model_path = self.ocr_config.get("qwen_model_path")
            if not model_path or not Path(model_path).exists():
                logger.warning(f"Qwen-VL model not found at {model_path}")
                return

            try:
                # Load Qwen-VL with vision support
                self.qwen_model = Llama(
                    model_path=model_path,
                    n_ctx=4096,
                    n_gpu_layers=-1,  # Use GPU if available
                    logits_all=True,
                    verbose=False,
                )
                logger.info(f"✅ Qwen-VL model loaded from {model_path}")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Qwen-VL model init failed: {e}")
                self.qwen_model = None

    def _ocr_image_qwen(self, fp: Path) -> str:
        """Run Qwen-VL OCR on an image; specialized for tables and complex layouts."""
        if not LLAMA_CPP_AVAILABLE or not BASE64_AVAILABLE:
            logger.warning("Qwen-VL dependencies not available")
            return ""

        self._load_qwen_model()
        if self.qwen_model is None:
            return ""

        try:
            # Encode image to base64
            with open(fp, "rb") as img_file:
                img_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Construct vision prompt for OCR with table focus
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_data}"},
                        },
                        {
                            "type": "text",
                            "text": "Extract all text from this image. If there are tables, preserve their structure using markdown table format. Be accurate and complete.",
                        },
                    ],
                }
            ]

            # Get OCR response
            response = self.qwen_model.create_chat_completion(
                messages=messages,
                temperature=0.1,  # Low temperature for accuracy
                max_tokens=2048,
            )

            # Extract text from response
            if response and "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0].get("message", {}).get("content", "")
                if content.strip():
                    logger.info(f"✅ Qwen-VL OCR succeeded for {fp.name}")
                    return content.strip()

            logger.warning(f"Qwen-VL returned empty response for {fp}")
            return ""

        except Exception as e:  # noqa: BLE001
            logger.error(f"OCR Qwen-VL failed {fp}: {e}")
            self.failed_tracker.add_failed_file(str(fp), str(e), "ocr_qwen")
            return ""

    def _choose_engine(self, fp: Path) -> str:
        """Decide which OCR engine to use for an image based on config and table detection."""
        mode = self.ocr_config.get("engine", "auto").lower()
        if mode in {"easyocr", "qwen"}:
            return mode

        has_table = False
        if CV_AVAILABLE:
            try:
                has_table = self._detect_table(fp)
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Table detection failed {fp}: {e}")

        return "qwen" if has_table else "easyocr"

    def _detect_table(self, fp: Path) -> bool:
        """Heuristic table detection using OpenCV lines/intersections."""
        if not CV_AVAILABLE:
            return False

        img = cv2.imread(str(fp), cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False

        max_dim = 1200
        h, w = img.shape[:2]
        scale = max_dim / max(h, w) if max(h, w) > max_dim else 1.0
        if scale != 1.0:
            img = cv2.resize(img, (int(w * scale), int(h * scale)))
            h, w = img.shape[:2]

        bw = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 15, 15)

        horiz = bw.copy()
        vert = bw.copy()
        scale_h = max(10, w // 100)
        scale_v = max(10, h // 100)
        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (scale_h, 1))
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, scale_v))
        horiz = cv2.erode(horiz, horiz_kernel, iterations=1)
        horiz = cv2.dilate(horiz, horiz_kernel, iterations=1)
        vert = cv2.erode(vert, vert_kernel, iterations=1)
        vert = cv2.dilate(vert, vert_kernel, iterations=1)

        table_mask = cv2.bitwise_and(horiz, vert)

        line_pixels = int(cv2.countNonZero(horiz) + cv2.countNonZero(vert))
        total_pixels = h * w
        density = line_pixels / max(total_pixels, 1)

        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        area = sum(cv2.contourArea(c) for c in contours)
        rel_area = area / max(total_pixels, 1)

        inter_points = cv2.bitwise_and(horiz, vert)
        inter_cnt, _ = cv2.findContours(inter_points, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        intersections_count = len(inter_cnt)

        cfg = self.ocr_config
        if (
            rel_area >= cfg.get("table_area_min", 0.15)
            and intersections_count >= cfg.get("min_intersections", 4)
            and density >= cfg.get("min_line_density", 0.0005)
        ):
            return True
        return False

    def _ensure_schema(self) -> None:
        """Ensure LanceDB table has required columns; add ocr_engine if missing."""
        if self.table is None:
            return
        try:
            schema = self.table.schema
            field_names = {f.name for f in schema}
            if "ocr_engine" in field_names:
                return

            # LanceDB version here lacks add_column; recreate table with new field
            data_tbl = self.table.to_arrow()
            records = data_tbl.to_pylist()
            for rec in records:
                rec.setdefault("ocr_engine", "")

            self.table = self.db.create_table(
                self.collection_name,
                data=records,
                mode="overwrite",
            )
            logger.info("🛠️ Recreated collection with 'ocr_engine' column")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Could not ensure schema for 'ocr_engine': {e}")

    def index_folder(
        self, folder: Path | str, recursive: bool = True, exts: Optional[set[str]] = None
    ) -> int:
        """Index all supported files under a folder.

        Args:
            folder: Root directory to traverse
            recursive: Recurse into subdirectories when True
            exts: Optional whitelist of extensions (e.g., {'.pdf', '.md'}). Defaults to common text/doc formats.

        Returns:
            Number of successfully indexed files
        """
        if not self.is_enabled():
            logger.warning("Indexing skipped: indexer not initialized.")
            return 0

        root = Path(folder)
        if not root.exists() or not root.is_dir():
            logger.warning(f"⚠️ Folder not found: {root}")
            return 0

        # Default extensions – common text and document formats
        if exts is None:
            exts = {".txt", ".md", ".pdf", ".docx", ".pptx", ".odt", ".html", ".json"}

        files: list[Path] = []
        if recursive:
            for dirpath, _, filenames in os.walk(root):
                for name in filenames:
                    p = Path(dirpath) / name
                    if p.suffix.lower() in exts:
                        files.append(p)
        else:
            for child in root.iterdir():
                if child.is_file() and child.suffix.lower() in exts:
                    files.append(child)

        logger.info(f"📂 Found {len(files)} file(s) to index in {root}")
        return self.index_files(files)

    def search(self, query: str, limit: int = 5) -> list[dict]:
        """Search indexed documents by semantic similarity.

        Args:
            query: Search query text
            limit: Maximum number of results to return

        Returns:
            List of matching documents with similarity scores
        """
        if not self.is_enabled() or self.table is None:
            logger.warning("Search skipped: no indexed documents.")
            return []

        try:
            # Generate embedding for query
            query_embedding = self.embedding_model.encode(query).tolist()

            # Search LanceDB by vector similarity
            results = self.table.search(query_embedding).limit(limit).to_list()

            logger.info(f"✅ Search '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"❌ Search failed: {e}")
            return []

    def get_stats(self) -> dict:
        """Get indexing statistics (document count, storage size, etc.)."""
        if self.table is None:
            return {"document_count": 0, "collection": self.collection_name}

        try:
            count = self.table.count_rows()
            failed_stats = self.failed_tracker.get_stats()
            return {
                "document_count": count,
                "collection": self.collection_name,
                "failed_files": failed_stats
            }
        except Exception as e:
            logger.error(f"❌ Failed to get stats: {e}")
            return {"error": str(e)}
    
    def retry_failed_files(self, max_retries: int = 3) -> int:
        """Retry indexing files that previously failed.
        
        Args:
            max_retries: Maximum retry attempts per file
            
        Returns:
            Number of successfully indexed files
        """
        failed_files = self.failed_tracker.get_failed_files(max_retries)
        
        if not failed_files:
            logger.info("No failed files to retry")
            return 0
        
        logger.info(f"Retrying {len(failed_files)} failed file(s)...")
        
        for file_path in failed_files:
            self.failed_tracker.increment_retry(file_path)
        
        # Attempt to index
        count = self.index_files(failed_files)
        
        logger.info(f"Successfully indexed {count}/{len(failed_files)} previously failed files")
        return count


__all__ = ["AITaoIndexer"]
