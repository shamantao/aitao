import sys
import os
import argparse

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.core.rag import rag
except ImportError:
    print("❌ Impossible de charger le moteur RAG")
    sys.exit(1)

def test_query(query):
    print(f"❓ Question : {query}")
    print("-" * 50)
    
    # Recherche RAG
    # On augmente un peu n_results pour voir ce qui remonte
    # Threshold infini pour voir les distances réelles sans filtre
    results = rag.search(query, n_results=5, threshold=99.0) 
    
    if not results:
        print("📭 Aucun résultat trouvé (Vraiment aucun ! La table est vide ou erreur de lecture).")
        return

    print(f"✅ {len(results)} fragments trouvés (sans filtre):\n")
    for i, res in enumerate(results):
        meta = res.get('meta', {})
        filename = meta.get('filename', 'Inconnu')
        score = res.get('score', 0) # C'est une distance L2 inversée ou similarité
        text = res.get('text', '').strip()
        
        # Aperçu
        print(f"📄 [{i+1}] {filename} (Score calculé: {score:.3f})")
        print(f"   (Distance réelle approx: {1-score:.3f})")
        print(f"   \"{text[:200]}...\"")
        print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test rapide du RAG")
    parser.add_argument("query", nargs="?", default="c'est quoi aitao ?", help="Question à poser")
    args = parser.parse_args()
    
    test_query(args.query)
