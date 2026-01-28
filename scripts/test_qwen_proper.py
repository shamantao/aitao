#!/usr/bin/env python3
"""
Test Qwen2.5-VL with the CORRECT chat handler.
According to llama-cpp-python docs, Qwen2.5-VL requires Qwen25VLChatHandler.
"""

import sys
import base64
from pathlib import Path

# Add project root
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.core.path_manager import path_manager

def test_qwen_proper():
    """Test Qwen-VL with correct chat handler."""
    print("=" * 70)
    print("🔧 DIAGNOSTIC: Qwen-VL with Qwen25VLChatHandler")
    print("=" * 70)
    
    # Import
    try:
        from llama_cpp import Llama
        from llama_cpp.llama_chat_format import Qwen25VLChatHandler
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("\nPossible fixes:")
        print("1. Update llama-cpp-python: pip install -U llama-cpp-python")
        print("2. Or Qwen25VLChatHandler not available in 0.3.16")
        return 1
    
    # Get model
    ocr_cfg = path_manager.get_ocr_config()
    model_path = ocr_cfg.get("qwen_model_path", "")
    
    if not Path(model_path).exists():
        print(f"❌ Model not found: {model_path}")
        return 1
    
    print(f"✅ Model: {Path(model_path).name}")
    
    # Test image
    test_img = Path("/Users/phil/Downloads/_Volumes/img/594771262836835204.jpg")
    
    if not test_img.exists():
        print(f"❌ Test image not found: {test_img}")
        return 1
    
    print(f"📄 Test image: {test_img.name}")
    print(f"   Size: {test_img.stat().st_size / 1024:.1f} KB")
    
    # Load model with proper handler
    print("\n⏳ Loading Qwen-VL with Qwen25VLChatHandler...")
    try:
        # Create chat handler
        chat_handler = Qwen25VLChatHandler(clip_model_path=None)  # May need separate clip model?
        
        # Load model
        llm = Llama(
            model_path=model_path,
            chat_handler=chat_handler,
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
        print("✅ Model loaded with chat handler")
    except Exception as e:
        print(f"❌ Load failed: {e}")
        print("\nCeci peut signifier:")
        print("1. Qwen2.5-VL GGUF n'a pas le clip model intégré")
        print("2. Il faut un fichier mmproj séparé (comme llava)")
        print("3. OU ce modèle GGUF ne supporte PAS la vision")
        return 1
    
    # Test with image
    print(f"\n🧪 Testing OCR on Chinese document...")
    
    # Read image as data URL
    with open(test_img, "rb") as f:
        img_data = base64.b64encode(f.read()).decode("utf-8")
    
    try:
        response = llm.create_chat_completion(
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image, keeping the original layout."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_data}"}},
                    ],
                }
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        
        if response and "choices" in response:
            text = response["choices"][0].get("message", {}).get("content", "")
            print(f"\n✅ Response ({len(text)} chars):")
            print(text[:500])
            
            if "blank" in text.lower():
                print("\n⚠️  STILL reports blank - ce modèle ne supporte PAS la vision!")
                return 1
            else:
                print("\n🎉 SUCCESS! Qwen-VL voit l'image!")
                return 0
        else:
            print("❌ Empty response")
            return 1
    except Exception as e:
        print(f"❌ Inference failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_qwen_proper())
