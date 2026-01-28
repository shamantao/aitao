#!/usr/bin/env python3
"""
Benchmark PaddleOCR (text + table) on sample docs.
- Uses PaddleOCR with table mode for pages likely containing tables.
- Compares table vs non-table modes on the same file.
- Writes outputs to $storage_root/ocr_cache/bench_paddle_ocr.
- Prints a concise summary (time + first 200 chars).
"""

import sys
import time
from pathlib import Path
from typing import Dict, Tuple

# Project path setup
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

try:
    from src.core.path_manager import path_manager
except ImportError:  # pragma: no cover
    from core.path_manager import path_manager  # type: ignore

try:
    from paddleocr import PaddleOCR, PPStructureV3, TableStructureRecognition
except Exception as exc:  # pragma: no cover
    print("❌ paddleocr is not installed. Install with: pip install paddleocr")
    print(f"Error: {exc}")
    sys.exit(1)

# Sample files to test
TEST_FILES = [
    Path("/Users/phil/Downloads/_Volumes/Adobe Scan 28 sept. 2025.pdf"),
    Path("/Users/phil/Downloads/_Volumes/Formulaire de sortie.pdf"),
    Path("/Users/phil/Downloads/_Volumes/僑外II.pdf"),
    Path("/Users/phil/Downloads/_Volumes/img/594771262836835204.jpg"),
    Path("/Users/phil/Downloads/_Volumes/img/596509779968131314.jpg"),
]

OUTPUT_DIR = Path(path_manager.get_storage_root()) / "ocr_cache" / "bench_paddle_ocr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def ensure_reader(table: bool = False) -> PaddleOCR:
    """Create a PaddleOCR reader. (table mode not available in 3.3.3)"""
    return PaddleOCR(
        use_textline_orientation=True,
        lang="ch",  # Chinese support (Traditional + Simplified)
    )


def run_ocr(reader, file_path: Path, is_table: bool) -> Tuple[str, float]:
    """Run PaddleOCR and return (text, elapsed_seconds)."""
    start = time.perf_counter()
    result = reader.ocr(str(file_path))
    elapsed = time.perf_counter() - start

    lines = []
    for page in result:
        if not page:
            continue
        for line in page:
            if len(line) >= 2:
                # Extract text from result tuple
                text_data = line[1]
                if isinstance(text_data, (list, tuple)) and len(text_data) > 0:
                    lines.append(str(text_data[0]))
                elif isinstance(text_data, str):
                    lines.append(str(text_data))
    return "\n".join(lines), elapsed


def save_output(file_path: Path, mode: str, content: str, elapsed: float) -> None:
    """Save OCR output to the cache directory."""
    safe_name = file_path.name.replace("/", "_")
    out_file = OUTPUT_DIR / f"{safe_name}.{mode}.txt"
    out_file.write_text(content, encoding="utf-8")
    print(f"📝 Saved {mode} output -> {out_file} ({elapsed:.2f}s)")


def benchmark() -> None:
    print("=" * 70)
    print("🔍 PaddleOCR benchmark (text mode only)")
    print("Outputs stored in:", OUTPUT_DIR)
    print("=" * 70)

    files = [p for p in TEST_FILES if p.exists()]
    missing = [p for p in TEST_FILES if not p.exists()]
    if missing:
        print("⚠️ Missing files:")
        for m in missing:
            print("  -", m)
    if not files:
        print("❌ No test files found; aborting.")
        return

    reader = ensure_reader(table=False)

    summary: Dict[str, str] = {}

    for fp in files:
        print(f"\n📄 {fp.name}")

        text_out, t_time = run_ocr(reader, fp, is_table=False)
        save_output(fp, "text", text_out, t_time)
        summary[fp.name] = f"{t_time:.2f}s | {text_out[:200].replace(chr(10), ' ')}"

    print("\n" + "=" * 70)
    print("Résumé (temps + premiers 200 caractères)")
    for fname, data in summary.items():
        print(f"- {fname}")
        print(f"  {data}")
    print("=" * 70)


if __name__ == "__main__":
    benchmark()
