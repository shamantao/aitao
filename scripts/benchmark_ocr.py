#!/usr/bin/env python3
"""
Benchmark Qwen-VL vs EasyOCR on real test files.
Tests both OCR engines on same files and compares:
- Loading time
- Processing time per file
- Text quality (manual evaluation)
- Table preservation (manual evaluation)

Usage:
    python benchmark_ocr.py /path/to/test/file1.pdf /path/to/test/file2.jpg ...
"""

import sys
import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any

# Add project root
BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
except ImportError:
    from core.path_manager import path_manager
    from core.logger import get_logger

logger = get_logger("BenchmarkOCR", "benchmark_ocr.log")

def benchmark_easyocr(image_paths: List[Path]) -> List[Dict[str, Any]]:
    """Benchmark EasyOCR on images."""
    logger.info("\n" + "=" * 70)
    logger.info("🔵 BENCHMARK: EasyOCR")
    logger.info("=" * 70)
    
    try:
        import easyocr
    except ImportError:
        logger.error("❌ EasyOCR not installed")
        return []
    
    # Initialize (measure load time)
    logger.info("⏳ Initializing EasyOCR...")
    load_start = time.time()
    try:
        reader = easyocr.Reader(['en'], gpu=False)
        load_time = time.time() - load_start
        logger.info(f"✅ EasyOCR loaded in {load_time:.2f}s")
    except Exception as e:
        logger.error(f"❌ Failed to load EasyOCR: {e}")
        return []
    
    results = []
    for img_path in image_paths:
        logger.info(f"\n📄 Processing: {img_path.name}")
        
        try:
            start = time.time()
            text_results = reader.readtext(str(img_path), detail=0, paragraph=True)
            text = "\n".join(text_results)
            elapsed = time.time() - start
            
            char_count = len(text)
            word_count = len(text.split())
            
            logger.info(f"   ⏱️  Time: {elapsed:.2f}s")
            logger.info(f"   📊 Output: {char_count} chars, {word_count} words")
            logger.info(f"   📝 Sample: {text[:100]}...")
            
            results.append({
                "file": str(img_path),
                "filename": img_path.name,
                "tool": "easyocr",
                "load_time": load_time if results == [] else 0,  # Only count once
                "process_time_sec": elapsed,
                "char_count": char_count,
                "word_count": word_count,
                "text_sample": text[:200],
                "full_text": text,
                "success": True,
            })
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            results.append({
                "file": str(img_path),
                "filename": img_path.name,
                "tool": "easyocr",
                "success": False,
                "error": str(e),
            })
    
    return results

def benchmark_qwen(image_paths: List[Path]) -> List[Dict[str, Any]]:
    """Benchmark Qwen-VL on images."""
    logger.info("\n" + "=" * 70)
    logger.info("🟢 BENCHMARK: Qwen-VL")
    logger.info("=" * 70)
    
    try:
        from llama_cpp import Llama
        import base64
    except ImportError:
        logger.error("❌ llama-cpp-python not installed")
        return []
    
    # Get model path
    ocr_cfg = path_manager.get_ocr_config()
    model_path = ocr_cfg.get("qwen_model_path", "")
    
    if not model_path or not Path(model_path).exists():
        logger.error(f"❌ Qwen model not found: {model_path}")
        return []
    
    # Initialize (measure load time)
    logger.info("⏳ Loading Qwen-VL model...")
    load_start = time.time()
    try:
        model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_gpu_layers=-1,
            logits_all=True,
            verbose=False,
        )
        load_time = time.time() - load_start
        logger.info(f"✅ Qwen-VL loaded in {load_time:.2f}s")
    except Exception as e:
        logger.error(f"❌ Failed to load Qwen: {e}")
        return []
    
    results = []
    for img_path in image_paths:
        logger.info(f"\n📄 Processing: {img_path.name}")
        
        try:
            # Encode image
            with open(img_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            
            # Prepare prompt
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
            
            # Run inference
            start = time.time()
            response = model.create_chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=2048,
            )
            elapsed = time.time() - start
            
            # Extract text
            text = ""
            if response and "choices" in response:
                text = response["choices"][0].get("message", {}).get("content", "")
            
            char_count = len(text)
            word_count = len(text.split())
            
            logger.info(f"   ⏱️  Time: {elapsed:.2f}s")
            logger.info(f"   📊 Output: {char_count} chars, {word_count} words")
            logger.info(f"   📝 Sample: {text[:100]}...")
            
            results.append({
                "file": str(img_path),
                "filename": img_path.name,
                "tool": "qwen",
                "load_time": load_time if len(results) == 0 else 0,
                "process_time_sec": elapsed,
                "char_count": char_count,
                "word_count": word_count,
                "text_sample": text[:200],
                "full_text": text,
                "success": True,
            })
        except Exception as e:
            logger.error(f"   ❌ Error: {e}")
            results.append({
                "file": str(img_path),
                "filename": img_path.name,
                "tool": "qwen",
                "success": False,
                "error": str(e),
            })
    
    return results

def generate_report(easy_results: List[Dict], qwen_results: List[Dict]) -> Dict:
    """Generate comparison report."""
    logger.info("\n" + "=" * 70)
    logger.info("📊 RAPPORT COMPARATIF")
    logger.info("=" * 70)
    
    # Calculate averages
    easy_times = [r["process_time_sec"] for r in easy_results if r.get("success")]
    qwen_times = [r["process_time_sec"] for r in qwen_results if r.get("success")]
    
    easy_avg = sum(easy_times) / len(easy_times) if easy_times else 0
    qwen_avg = sum(qwen_times) / len(qwen_times) if qwen_times else 0
    
    report = {
        "benchmark_date": "2026-01-27",
        "files_tested": len(easy_results),
        "easyocr": {
            "load_time_sec": easy_results[0].get("load_time", 0) if easy_results else 0,
            "avg_process_time_sec": easy_avg,
            "success_count": len([r for r in easy_results if r.get("success")]),
            "results": easy_results,
        },
        "qwen": {
            "load_time_sec": qwen_results[0].get("load_time", 0) if qwen_results else 0,
            "avg_process_time_sec": qwen_avg,
            "success_count": len([r for r in qwen_results if r.get("success")]),
            "results": qwen_results,
        },
        "comparison": {
            "qwen_slower_factor": qwen_avg / easy_avg if easy_avg > 0 else 0,
            "recommendation": "Manual evaluation required for quality assessment",
        }
    }
    
    # Display summary
    logger.info(f"\n🔵 EasyOCR:")
    logger.info(f"   Load time: {report['easyocr']['load_time_sec']:.2f}s")
    logger.info(f"   Avg process: {easy_avg:.2f}s/file")
    logger.info(f"   Success: {report['easyocr']['success_count']}/{len(easy_results)}")
    
    logger.info(f"\n🟢 Qwen-VL:")
    logger.info(f"   Load time: {report['qwen']['load_time_sec']:.2f}s")
    logger.info(f"   Avg process: {qwen_avg:.2f}s/file")
    logger.info(f"   Success: {report['qwen']['success_count']}/{len(qwen_results)}")
    
    logger.info(f"\n📈 Comparison:")
    if qwen_avg > 0 and easy_avg > 0:
        logger.info(f"   Qwen is {report['comparison']['qwen_slower_factor']:.1f}x slower than EasyOCR")
    
    return report

def main():
    """Run benchmark."""
    if len(sys.argv) < 2:
        print("Usage: python benchmark_ocr.py <image1> <image2> ...")
        print("\nExample:")
        print("  python benchmark_ocr.py test1.jpg test2.pdf test3.png")
        return 1
    
    image_paths = [Path(p) for p in sys.argv[1:]]
    
    # Validate files
    valid_paths = []
    for p in image_paths:
        if not p.exists():
            logger.warning(f"⚠️  File not found: {p}")
        elif p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".pdf"}:
            logger.warning(f"⚠️  Unsupported format: {p}")
        else:
            valid_paths.append(p)
    
    if not valid_paths:
        logger.error("❌ No valid files to test")
        return 1
    
    logger.info("=" * 70)
    logger.info(f"🧪 OCR BENCHMARK: {len(valid_paths)} file(s)")
    logger.info("=" * 70)
    
    for p in valid_paths:
        logger.info(f"   📄 {p.name}")
    
    # Run benchmarks
    easy_results = benchmark_easyocr(valid_paths)
    qwen_results = benchmark_qwen(valid_paths)
    
    # Generate report
    report = generate_report(easy_results, qwen_results)
    
    # Save to file
    output_file = Path(__file__).parent / "benchmark_results.json"
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\n💾 Full report saved: {output_file}")
    logger.info("\n✅ Benchmark complete!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
