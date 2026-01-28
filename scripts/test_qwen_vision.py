#!/usr/bin/env python3
"""
Direct test of Qwen-VL on a real image.
Tests if Qwen can actually see the image content.
"""

import sys
import base64
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.core.path_manager import path_manager

def test_qwen_direct():
    """Test Qwen-VL directly on an image."""
    print("=" * 70)
    print("🔍 DIAGNOSTIC: Qwen-VL Vision Test")
    print("=" * 70)
    
    # Import Qwen
    try:
        from llama_cpp import Llama
    except ImportError:
        print("❌ llama-cpp-python not installed")
        return 1
    
    # Get model
    ocr_cfg = path_manager.get_ocr_config()
    model_path = ocr_cfg.get("qwen_model_path", "")
    
    if not Path(model_path).exists():
        print(f"❌ Model not found: {model_path}")
        return 1
    
    print(f"✅ Model: {Path(model_path).name}")
    
    # Load model
    print("\n⏳ Loading Qwen-VL...")
    try:
        model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_gpu_layers=-1,
            logits_all=True,
            verbose=False,
        )
        print("✅ Model loaded")
    except Exception as e:
        print(f"❌ Load failed: {e}")
        return 1
    
    # Test image
    test_img = Path("/Users/phil/Downloads/_Volumes/img/594771262836835204.jpg")
    
    if not test_img.exists():
        print(f"❌ Test image not found: {test_img}")
        return 1
    
    print(f"\n📄 Testing: {test_img.name}")
    print(f"   Size: {test_img.stat().st_size / 1024:.1f} KB")
    
    # Read and encode
    try:
        with open(test_img, "rb") as f:
            img_data = base64.b64encode(f.read()).decode("utf-8")
        print(f"   Base64: {len(img_data)} chars")
    except Exception as e:
        print(f"❌ Encoding failed: {e}")
        return 1
    
    # Try multiple prompts to see which works
    prompts = [
        "Describe what you see in this image.",
        "What text is visible in this image?",
        "Extract all text from this image.",
        "这张图片里有什么文字？",  # Chinese: What text is in this image?
    ]
    
    for i, prompt_text in enumerate(prompts, 1):
        print(f"\n🧪 Test {i}: {prompt_text[:50]}...")
        
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
                        "text": prompt_text,
                    },
                ],
            }
        ]
        
        try:
            response = model.create_chat_completion(
                messages=messages,
                temperature=0.1,
                max_tokens=512,
            )
            
            if response and "choices" in response:
                text = response["choices"][0].get("message", {}).get("content", "")
                print(f"   Response ({len(text)} chars):")
                print(f"   {text[:200]}...")
                
                if "blank" in text.lower() or "no text" in text.lower():
                    print("   ⚠️  Model thinks image is blank!")
                else:
                    print("   ✅ Model sees content!")
            else:
                print("   ❌ Empty response")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("CONCLUSION:")
    print("Si toutes les réponses disent 'blank', le problème est:")
    print("1. Qwen2.5-VL ne supporte PAS la vision (juste texte)")
    print("2. OU mauvais format d'image pour Qwen")
    print("3. OU version llama-cpp-python incompatible")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(test_qwen_direct())
