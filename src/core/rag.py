import os
import lancedb
import json
from sentence_transformers import SentenceTransformer

try:
    from src.core.path_manager import path_manager
except ImportError:
    try:
        from core.path_manager import path_manager
    except ImportError:
         # Fallback for relative run if needed
         import sys
         sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
         from src.core.path_manager import path_manager

class RagEngine:
    def __init__(self, table_name="aitao_knowledge"):
        # Récupération du chemin via PathManager
        self.persist_dir = path_manager.get_vector_db_path()
        
        # Assurer que le dossier existe
        os.makedirs(self.persist_dir, exist_ok=True)
        
        # Initialisation du client LanceDB
        self.db = lancedb.connect(self.persist_dir)
        self.table_name = table_name
        
        # Modèle d'embedding (384 dimensions)
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialisation "Lazy"
        self.table = None
        self._ensure_open()

    def _get_embedding(self, text: str) -> list[float]:
        return self.embedder.encode(text).tolist()

    def _ensure_open(self):
        """Helper pour s'assurer que la table est ouverte avant lecture."""
        if self.table is not None:
            return

        tables = self.db.list_tables()
        # Handle LanceDB v0.x vs Newer API iterator
        if hasattr(tables, "tables"):
            tables = tables.tables
        elif not isinstance(tables, list):
             tables = list(tables)
             
        if self.table_name in tables:
            self.table = self.db.open_table(self.table_name)
        else:
            # Table n'existe physique pas
            pass

    def add_document(self, text: str, metadata: dict = None):
        """Ajoute un document à la base vectorielle."""
        if metadata is None:
            metadata = {}
            
        vector = self._get_embedding(text)
        
        # Extraction de 'source' pour en faire une colonne indexable/filtrable
        source_path = metadata.get("source", "unknown")
        
        data = [{
            "vector": vector,
            "text": text,
            "source": source_path, # Promoted to top-level column
            "metadata": json.dumps(metadata)
        }]
        
        self._ensure_table(data)
        self.table.add(data)
        
    def add_documents_batch(self, items: list):
        """Ajoute plusieurs documents d'un coup (optimisé).
        items = [{'text': '...', 'metadata': {...}}, ...]
        """
        if not items:
            return

        # Pre-calculate embeddings in batch if possible, currently detailed loop
        # For simplicity in this structure:
        data_batch = []
        for item in items:
            txt = item["text"]
            meta = item.get("metadata", {})
            vec = self._get_embedding(txt)
            src = meta.get("source", "unknown")
            
            data_batch.append({
                "vector": vec,
                "text": txt,
                "source": src,
                "metadata": json.dumps(meta)
            })
            
        self._ensure_table(data_batch)
        self.table.add(data_batch)
        print(f"✅ Lot de {len(items)} documents ajouté")

    def delete_by_source(self, source_path: str):
        """Supprime toutes les entrées liées à un fichier source spécifique."""
        if self.table is None:
            if self.table_name in self.db.list_tables():
                self.table = self.db.open_table(self.table_name)
            else:
                return # Table doesn't exist, nothing to delete

        try:
            # Echappement basique pour éviter les erreurs de syntaxe SQL LanceDB
            safe_source = source_path.replace("'", "''")
            
            # Suppression utilisant la colonne 'source' (si elle existe)
            # Si c'est un vieux schéma sans colonne source, ça peut fail, mais LanceDB gère l'évolution.
            self.table.delete(f"source = '{safe_source}'")
            # print(f"♻️ Nettoyage précédent de : {source_path}")
        except Exception as e:
            # Peut arriver si la colonne source n'existe pas encore dans le schéma
            # On ignore silencieusement ou on log
            # print(f"⚠️ Warning delete: {e}")
            pass

    def _ensure_table(self, initial_data):
        if self.table is None:
            if self.table_name in self.db.list_tables():
                self.table = self.db.open_table(self.table_name)
            else:
                try:
                    self.table = self.db.create_table(self.table_name, initial_data)
                except Exception:
                    self.table = self.db.open_table(self.table_name)

    def search(self, query: str, n_results: int = 3, threshold: float = 0.5):
        """Cherche les documents les plus pertinents."""
        self._ensure_open()
             
        if self.table is None:
            print("⚠️ Erreur RAG: Table non initialisée ou vide.")
            return []

        query_vector = self._get_embedding(query)
        
        # LanceDB search
        try:
            results = self.table.search(query_vector).limit(n_results).to_list()
        except Exception as e:
            print(f"⚠️ Erreur LanceDB Search: {e}")
            return []
        
        found_docs = []
        for r in results:
            # Score de distance (L2 par défaut souvent, ou cosine selon config, ici par défaut L2 dans lancedb simple)
            # LanceDB retourne la distance. Plus elle est petite, plus c'est proche.
            # Avec des vecteurs normalisés, Cosine Distance = Dist.
            dist = r['_distance']
            
            # Application du seuil (empirique, à ajuster)
            # LOG DEBUG TEMPORAIRE
            # print(f"[DEBUG RAG] Dist: {dist} vs Threshold: {threshold}")
            
            if dist > threshold:
                continue

            # Parsing metadata
            try:
                meta = json.loads(r['metadata'])
            except:
                meta = {}
                
            found_docs.append({
                "text": r['text'],
                "meta": meta,
                "score": 1 - dist # Pseudo-score de similarité
            })
                
        return found_docs

    def get_stats(self):
        """Retourne les statistiques de la base de données."""
        if self.table is None: 
            if self.table_name in self.db.list_tables():
                self.table = self.db.open_table(self.table_name)
        
        count = 0
        if self.table:
            # LanceDB v2+ : count_rows() ou len(table)
            try:
                count = len(self.table)
            except:
                # Fallback pour certaines versions
                try: 
                    count = self.table.count_rows() 
                except:
                    # En dernier recours, iterer (lent) ou 0
                    count = "N/A"
        return {
            "documents": count,
            "path": PERSIST_DIR
        }

    def reset_memory(self):
        """Efface toute la mémoire."""
        try:
            self.db.drop_table(self.table_name)
            self.table = None
            return True
        except Exception as e:
            print(f"Erreur reset: {e}")
            return False

# Instance globale
rag = RagEngine()

if __name__ == "__main__":
    print("Test du moteur RAG (LanceDB)...")
    rag.add_document("Phil est le créateur du projet Aitao.", {"category": "identity", "source": "manual"})
    rag.add_document("Aitao utilise LanceDB pour sa mémoire.", {"category": "tech"})
    
    results = rag.search("Qui est le créateur ?", threshold=1.5) # Seuil large pour test
    print("Résultats :")
    for res in results:
        print(f"- [{res['score']:.4f}] {res['text']} (Meta: {res['meta']})")
