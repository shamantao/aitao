#!/usr/bin/env python3
"""
Complete Qwen-VL benchmark with mmproj.
Tests Qwen2.5-VL vision OCR on 5 documents (3 PDFs + 2 images).
Compares with PaddleOCR results.
"""

import sys
import time
import json
from pathlib import Path
from typing import Tuple, Dict

# Project path setup
BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

try:
    from src.core.path_manager import path_manager
except ImportError:  # pragma: no cover
    from core.path_manager import path_manager  # type: ignore

try:
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Qwen25VLChatHandler
except Exception as exc:  # pragma: no cover
    print(f"❌ llama-cpp-python not installed: {exc}")
    sys.exit(1)

# Test files
TEST_FILES = [
    Path("/Users/phil/Downloads/_Volumes/Adobe Scan 28 sept. 2025.pdf"),
    Path("/Users/phil/Downloads/_Volumes/Formulaire de sortie.pdf"),
    Path("/Users/phil/Downloads/_Volumes/僑外II.pdf"),
    Path("/Users/phil/Downloads/_Volumes/img/594771262836835204.jpg"),
    Path("/Users/phil/Downloads/_Volumes/img/596509779968131314.jpg"),
]

OUTPUT_DIR = Path(path_manager.get_storage_root()) / "ocr_cache" / "bench_qwen_vl"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = Path("/Users/phil/Downloads/_sources/AI-models/qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf")
MMPROJ_PATH = Path("/Users/phil/Downloads/_sources/AI-models/qwen2-vl-7b/Qwen2.5-VL-7B-Instruct-mmproj-bf16.gguf")


def load_qwen_vl() -> Llama:
    """Load Qwen-VL with mmproj vision handler."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    if not MMPROJ_PATH.exists():
        raise FileNotFoundError(f"MMProj not found: {MMPROJ_PATH}")
    
    print(f"Loading Qwen-VL with mmproj...")
    
    try:
        # Create vision handler with mmproj
        chat_handler = Qwen25VLChatHandler(clip_model_path=str(MMPROJ_PATH))
        
        # Load model with vision support
        llm = Llama(
            model_path=str(MODEL_PATH),
            chat_handler=chat_handler,
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
        print(f"✅ Qwen-VL loaded successfully with mmproj")
        return llm
    except Exception as e:
        print(f"❌ Failed to load Qwen-VL: {e}")
        raise


def convert_pdf_to_images(pdf_path: Path) -> list[Path]:
    """Convert PDF to temporary images for OCR."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        print(f"⚠️ pdf2image not installed, skipping PDF: {pdf_path.name}")
        return []
    
    try:
        import tempfile
        images = convert_from_path(str(pdf_path))
        
        # Save to temp dir
        temp_images = []
        temp_dir = Path(tempfile.gettempdir()) / "qwen_ocr_pdfs"
        temp_dir.mkdir(exist_ok=True)
        
        for i, img in enumerate(images):
            temp_path = temp_dir / f"{pdf_path.stem}_page{i}.png"
            img.save(temp_path, format="PNG")
            temp_images.append(temp_path)
        
        return temp_images
    except Exception as e:
        print(f"⚠️ PDF conversion failed for {pdf_path.name}: {e}")
        return []


def ocr_image_qwen(llm: Llama, image_path: Path) -> Tuple[str, float]:
    """Run Qwen-VL OCR on a single image."""
    import base64
    
    start = time.perf_counter()
    
    try:
        # Read and encode image
        with open(image_path, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        
        # Determine mimetype
        suffix = image_path.suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        mime_type = mime_map.get(suffix, "image/jpeg")
        
        # Send to Qwen-VL
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{img_data}"},
                    },
                    {
                        "type": "text",
                        "text": "Extract ALL text from this image. Preserve layout and structure. If there are tables, use markdown table format. Be complete and accurate.",
                    },
                ],
            }
        ]
        
        response = llm.create_chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
        )
        
        elapsed = time.perf_counter() - start
        
        # Extract text
        if response and "choices" in response and len(response["choices"]) > 0:
            content = response["choices"][0].get("message", {}).get("content", "")
            if content.strip() and "blank" not in content.lower():
                return content.strip(), elapsed
        
        return "", elapsed
    except Exception as e:
        elapsed = time.perf_counter() - start
        print(f"❌ OCR failed for {image_path.name}: {e}")
        return "", elapsed


def run_benchmark():
    """Run complete Qwen-VL benchmark."""
    print("=" * 70)
    print("🔍 Qwen2.5-VL Vision OCR Benchmark (with mmproj)")
    print("=" * 70)
    
    # Check files
    files = [p for p in TEST_FILES if p.exists()]
    missing = [p for p in TEST_FILES if not p.exists()]
    
    if missing:
        print("⚠️ Missing test files:")
        for m in missing:
            print(f"   - {m}")
    
    if not files:
        print("❌ No test files found!")
        return
    
    print(f"\n✅ Found {len(files)} test files\n")
    
    # Load model
    try:
        llm = load_qwen_vl()
    except Exception as e:
        print(f"❌ Cannot load model: {e}")
        return
    
    results: Dict[str, Dict[str, str]] = {}
    
    for test_file in files:
        print(f"\n📄 Processing: {test_file.name}")
        
        # Convert PDFs to images if needed
        if test_file.suffix.lower() == ".pdf":
            print(f"   Converting PDF to images...")
            images = convert_pdf_to_images(test_file)
            if not images:
                print(f"   ⚠️ Skipped (conversion failed)")
                continue
        else:
            images = [test_file]
        
        # Run OCR on each image
        all_text = []
        total_time = 0.0
        
        for img in images:
            text, elapsed = ocr_image_qwen(llm, img)
            total_time += elapsed
            
            if text:
                all_text.append(text)
                print(f"   ✅ Page OCR complete ({elapsed:.2f}s, {len(text)} chars)")
            else:
                print(f"   ⚠️ No text extracted ({elapsed:.2f}s)")
        
        # Combine results
        combined = "\n\n".join(all_text)
        
        # Save
        out_file = OUTPUT_DIR / f"{test_file.name}.qwen_vl.txt"
        out_file.write_text(combined, encoding="utf-8")
        
        preview = combined[:200].replace("\n", " ")
        results[test_file.name] = {
            "time": f"{total_time:.2f}s",
            "chars": str(len(combined)),
            "preview": preview,
        }
        
        print(f"   📝 Saved → {out_file.name}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ")
    print("=" * 70)
    
    for fname, data in results.items():
        print(f"\n{fname}")
        print(f"  Time: {data['time']}")
        print(f"  Chars: {data['chars']}")
        print(f"  Preview: {data['preview']}")
    
    print("\n" + "=" * 70)
    print("✅ Benchmark complete!")
    print("Outputs saved to:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()
