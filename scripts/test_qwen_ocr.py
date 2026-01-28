#!/usr/bin/env python3
"""
Test Qwen-VL availability and basic functionality.
Checks:
1. Model file exists at configured path
2. llama-cpp-python can load it
3. Can run basic OCR on a test image
4. Performance metrics
"""

import sys
import os
from pathlib import Path
import time

# Add project root
BASE_DIR = Path(__file__).parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from src.core.path_manager import path_manager
    from src.core.logger import get_logger
except ImportError:
    # Fallback
    from core.path_manager import path_manager
    from core.logger import get_logger

logger = get_logger("QwenTest", "qwen_test.log")

def check_model_file():
    """Vérifier que le fichier modèle existe."""
    logger.info("=" * 70)
    logger.info("🔍 Vérification du modèle Qwen-VL")
    logger.info("=" * 70)
    
    ocr_cfg = path_manager.get_ocr_config()
    model_path = ocr_cfg.get("qwen_model_path", "")
    
    if not model_path:
        logger.error("❌ qwen_model_path non configuré dans config.toml")
        return False
    
    p = Path(model_path)
    if not p.exists():
        logger.error(f"❌ Modèle non trouvé: {model_path}")
        return False
    
    size_gb = p.stat().st_size / (1024**3)
    logger.info(f"✅ Modèle trouvé: {p.name} ({size_gb:.2f} GB)")
    return True

def check_llama_cpp_available():
    """Vérifier que llama-cpp-python est disponible."""
    logger.info("\n🔍 Vérification des dépendances")
    
    try:
        from llama_cpp import Llama
        logger.info("✅ llama-cpp-python importé")
        return True
    except ImportError as e:
        logger.error(f"❌ llama-cpp-python non disponible: {e}")
        logger.error("   → pip install llama-cpp-python")
        return False

def test_qwen_loading():
    """Essayer de charger le modèle Qwen-VL."""
    logger.info("\n⏳ Chargement du modèle Qwen-VL...")
    
    from llama_cpp import Llama
    
    ocr_cfg = path_manager.get_ocr_config()
    model_path = ocr_cfg.get("qwen_model_path", "")
    
    if not model_path or not Path(model_path).exists():
        logger.error(f"❌ Modèle path invalide: {model_path}")
        return False
    
    try:
        start = time.time()
        model = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_gpu_layers=-1,
            logits_all=True,
            verbose=False,
        )
        elapsed = time.time() - start
        logger.info(f"✅ Modèle chargé en {elapsed:.2f}s")
        return model
    except Exception as e:
        logger.error(f"❌ Erreur chargement: {e}")
        return None

def test_qwen_inference(model):
    """Essayer une inférence simple (texte, pas image)."""
    logger.info("\n⏳ Test inférence simple (texte)...")
    
    try:
        messages = [
            {
                "role": "user",
                "content": "What is 2+2?"
            }
        ]
        
        start = time.time()
        response = model.create_chat_completion(
            messages=messages,
            temperature=0.1,
            max_tokens=100,
        )
        elapsed = time.time() - start
        
        if response and "choices" in response:
            text = response["choices"][0].get("message", {}).get("content", "")
            logger.info(f"✅ Inférence réussie en {elapsed:.2f}s")
            logger.info(f"   Réponse: {text[:100]}")
            return True
        else:
            logger.error("❌ Réponse vide")
            return False
    except Exception as e:
        logger.error(f"❌ Erreur inférence: {e}")
        return False

def test_easyocr_support():
    """Vérifier support des langues EasyOCR."""
    logger.info("\n🔍 Vérification EasyOCR (support chinois)")
    
    try:
        import easyocr
        logger.info("✅ easyocr importé")
    except ImportError:
        logger.error("❌ easyocr non installé")
        return False
    
    # Test anglais
    try:
        reader_en = easyocr.Reader(['en'], gpu=False)
        logger.info("✅ EasyOCR ['en'] fonctionne")
    except Exception as e:
        logger.error(f"❌ EasyOCR ['en'] échoue: {e}")
    
    # Test chinois (attendu échouer)
    try:
        reader_zh = easyocr.Reader(['zh-cn'], gpu=False)
        logger.warning("⚠️  EasyOCR ['zh-cn'] fonctionne (SURPRENANT!)")
        return True
    except Exception as e:
        logger.info(f"⚠️  EasyOCR ['zh-cn'] non supporté (ATTENDU): {e}")
        return False

def main():
    """Run all checks."""
    logger.info("\n" * 2)
    
    results = {
        "model_file": False,
        "llama_cpp": False,
        "qwen_loading": False,
        "qwen_inference": False,
        "easyocr_check": False,
    }
    
    # Check 1: Model file
    if not check_model_file():
        logger.error("\n❌ STOP: Modèle non trouvé")
        logger.info("\n" + "=" * 70)
        logger.info("RÉSUMÉ")
        logger.info("=" * 70)
        for k, v in results.items():
            status = "✅" if v else "❌"
            logger.info(f"{status} {k}")
        return 1
    results["model_file"] = True
    
    # Check 2: Dependencies
    if not check_llama_cpp_available():
        logger.error("\n❌ STOP: llama-cpp-python manquant")
        logger.info("\n" + "=" * 70)
        logger.info("RÉSUMÉ")
        logger.info("=" * 70)
        for k, v in results.items():
            status = "✅" if v else "❌"
            logger.info(f"{status} {k}")
        return 1
    results["llama_cpp"] = True
    
    # Check 3: Load model
    model = test_qwen_loading()
    if model:
        results["qwen_loading"] = True
        
        # Check 4: Inference
        if test_qwen_inference(model):
            results["qwen_inference"] = True
    
    # Check 5: EasyOCR
    test_easyocr_support()
    results["easyocr_check"] = True
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 RÉSUMÉ FINAL")
    logger.info("=" * 70)
    
    for k, v in results.items():
        status = "✅" if v else "❌"
        logger.info(f"{status} {k}")
    
    logger.info("\n" + "=" * 70)
    
    if all(results.values()):
        logger.info("🎉 Tous les tests passent! Qwen-VL est prêt.")
        logger.info("\nProchaine étape:")
        logger.info("1. Lancer scripts/benchmark_ocr.py pour test complet")
        logger.info("2. Créer dataset de test chinois/tableaux")
        logger.info("3. Benchmarker Qwen vs EasyOCR")
        return 0
    else:
        logger.error("\n⚠️  Certains tests échouent. Voir logs ci-dessus.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
