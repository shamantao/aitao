import sys
import os
import lancedb
import json

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

try:
    from src.core.path_manager import path_manager
except ImportError:
    print("❌ Impossible de charger path_manager")
    sys.exit(1)

def check_rag():
    db_path = path_manager.get_vector_db_path()
    print(f"📂 Base de données : {db_path}")
    
    if not os.path.exists(db_path):
        print("❌ Le dossier de base de données n'existe pas.")
        return

    try:
        db = lancedb.connect(db_path)
        # Gestion compatibilité version LanceDB
        tables_res = db.list_tables()
        # Si c'est un itérateur ou objet complexe, on essaie de le convertir
        if hasattr(tables_res, "tables"):
             tables = tables_res.tables
        else:
             tables = list(tables_res)
             
        print(f"📚 Tables trouvées : {tables}")
        
        # On tente d'ouvrir directement
        try:
            table = db.open_table("aitao_knowledge")
        except Exception:
             print("⚠️ Table 'aitao_knowledge' introuvable (échec open_table).")
             return

        count = len(table)
        print(f"📊 Nombre total de fragments (chunks) : {count}")
        
        if count == 0:
            print("⚠️ La table est vide.")
            return

        # Check sample
        print("\n🔍 Exemple de contenu (5 premiers items) :")
        # On charge tout (26k c'est léger) et on prend les 5 premiers
        df = table.to_pandas().head(5)
        
        for idx, row in df.iterrows():
            meta = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
            filename = meta.get('filename', 'N/A')
            # source = row.get('source', 'N/A') # Depend du schéma
            preview = row['text'][:100].replace('\n', ' ')
            print(f" - [{filename}] : {preview}...")
            
    except Exception as e:
        print(f"❌ Erreur lors de l'inspection : {e}")

if __name__ == "__main__":
    check_rag()
