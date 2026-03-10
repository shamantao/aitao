#!/usr/bin/env python3
"""
MLX vs Ollama Benchmark Script.

Compares inference speed between MLX and Ollama backends
on the same prompt to measure performance gain on Apple Silicon.

Usage:
    python scripts/benchmark_mlx.py

Requirements:
    - Running Ollama server (http://localhost:11434)
    - MLX model downloaded (will download if not present)
    - Apple Silicon Mac (for MLX acceleration)
"""

import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.platform import get_platform_info
from src.core.logger import get_logger

logger = get_logger("benchmark")


# Test prompts of varying complexity
PROMPTS = [
    # Short prompt
    {
        "name": "Short",
        "prompt": "What is 2+2? Answer with just the number.",
        "max_tokens": 10,
    },
    # Medium prompt
    {
        "name": "Medium",
        "prompt": "Explain what a recursive function is in programming. Keep it brief.",
        "max_tokens": 100,
    },
    # Long prompt
    {
        "name": "Long",
        "prompt": """Write a Python function that implements binary search.
Include docstring and example usage. The function should:
1. Take a sorted list and target value
2. Return the index if found, -1 otherwise
3. Use iterative approach (not recursive)""",
        "max_tokens": 300,
    },
]


def benchmark_ollama(prompt: str, max_tokens: int, model: str = "llama3.1-local:latest") -> dict:
    """Benchmark Ollama inference."""
    import httpx
    
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": 0.7,
        }
    }
    
    start_time = time.time()
    
    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "backend": "ollama",
            "model": model,
            "success": True,
            "response_length": len(data.get("response", "")),
            "elapsed_ms": elapsed_ms,
            "eval_count": data.get("eval_count", 0),
            "eval_duration_ns": data.get("eval_duration", 0),
            "tokens_per_second": data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9) if data.get("eval_duration") else 0,
        }
    except Exception as e:
        return {
            "backend": "ollama",
            "model": model,
            "success": False,
            "error": str(e),
            "elapsed_ms": (time.time() - start_time) * 1000,
        }


def benchmark_mlx(prompt: str, max_tokens: int, model: str = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit") -> dict:
    """Benchmark MLX inference."""
    from src.llm.mlx_backend import MLXBackend
    
    backend = MLXBackend(default_model=model)
    
    if not backend.is_available():
        return {
            "backend": "mlx",
            "model": model,
            "success": False,
            "error": "MLX not available on this platform",
            "elapsed_ms": 0,
        }
    
    start_time = time.time()
    
    try:
        result = backend.generate(
            prompt=prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "backend": "mlx",
            "model": model,
            "success": True,
            "response_length": len(result.text),
            "elapsed_ms": elapsed_ms,
            "tokens_generated": result.tokens_generated,
            "tokens_per_second": result.tokens_per_second,
        }
    except Exception as e:
        return {
            "backend": "mlx",
            "model": model,
            "success": False,
            "error": str(e),
            "elapsed_ms": (time.time() - start_time) * 1000,
        }


def run_benchmark():
    """Run the full benchmark suite."""
    print("\n" + "=" * 70)
    print("🚀 MLX vs Ollama Benchmark")
    print("=" * 70)
    
    # Platform info
    platform = get_platform_info()
    print(f"\n📱 Platform: {platform.os} {platform.arch}")
    print(f"   Apple Silicon: {platform.is_apple_silicon}")
    print(f"   MLX Available: {platform.has_mlx}")
    print(f"   CPU Cores: {platform.cpu_cores}")
    print(f"   Memory: {platform.memory_gb:.1f} GB")
    
    results = []
    
    for test in PROMPTS:
        print(f"\n{'─' * 70}")
        print(f"📝 Test: {test['name']} (max_tokens={test['max_tokens']})")
        print(f"   Prompt: {test['prompt'][:50]}...")
        
        # Run Ollama benchmark
        print("\n   ⏱️  Ollama...", end=" ", flush=True)
        ollama_result = benchmark_ollama(test["prompt"], test["max_tokens"])
        if ollama_result["success"]:
            print(f"✅ {ollama_result['elapsed_ms']:.0f}ms ({ollama_result.get('tokens_per_second', 0):.1f} tok/s)")
        else:
            print(f"❌ {ollama_result.get('error', 'Unknown error')}")
        
        # Run MLX benchmark
        print("   ⏱️  MLX...", end=" ", flush=True)
        mlx_result = benchmark_mlx(test["prompt"], test["max_tokens"])
        if mlx_result["success"]:
            print(f"✅ {mlx_result['elapsed_ms']:.0f}ms ({mlx_result.get('tokens_per_second', 0):.1f} tok/s)")
        else:
            print(f"❌ {mlx_result.get('error', 'Unknown error')}")
        
        # Calculate speedup
        if ollama_result["success"] and mlx_result["success"]:
            speedup = ollama_result["elapsed_ms"] / mlx_result["elapsed_ms"]
            print(f"\n   📊 Speedup: {speedup:.2f}x {'(MLX faster)' if speedup > 1 else '(Ollama faster)'}")
        
        results.append({
            "test": test["name"],
            "ollama": ollama_result,
            "mlx": mlx_result,
        })
    
    # Summary
    print(f"\n{'=' * 70}")
    print("📊 SUMMARY")
    print("=" * 70)
    
    print(f"\n{'Test':<10} {'Ollama':<15} {'MLX':<15} {'Speedup':<10}")
    print("-" * 50)
    
    for r in results:
        ollama_time = f"{r['ollama']['elapsed_ms']:.0f}ms" if r['ollama']['success'] else "FAIL"
        mlx_time = f"{r['mlx']['elapsed_ms']:.0f}ms" if r['mlx']['success'] else "FAIL"
        
        if r['ollama']['success'] and r['mlx']['success']:
            speedup = r['ollama']['elapsed_ms'] / r['mlx']['elapsed_ms']
            speedup_str = f"{speedup:.2f}x"
        else:
            speedup_str = "N/A"
        
        print(f"{r['test']:<10} {ollama_time:<15} {mlx_time:<15} {speedup_str:<10}")
    
    print("\n" + "=" * 70)
    print("✅ Benchmark complete!")
    
    return results


if __name__ == "__main__":
    run_benchmark()
