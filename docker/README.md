# ☯️ AI Tao - Installation Rapide (macOS)

**AI Tao** est votre assistant IA local pour la recherche et traduction de documents, 100% privé.

---

## 🚀 Installation en 3 étapes

### Étape 1 : Installer Docker Desktop

Si Docker Desktop n'est pas installé :
👉 **[Télécharger Docker Desktop](https://www.docker.com/products/docker-desktop/)**

Après installation, lancez Docker Desktop et attendez que l'icône 🐳 soit stable.

---

### Étape 2 : Lancer l'installation

Ouvrez Terminal et exécutez :

```bash
cd /chemin/vers/ce/dossier
./install-aitao.sh
```

Le script va :
- ✅ Vérifier Docker
- ✅ Télécharger les composants
- ✅ Démarrer tous les services

---

### Étape 3 : Accéder à AI Tao

Une fois l'installation terminée, ouvrez dans votre navigateur :

| Service | URL |
|---------|-----|
| **Interface Web** | http://localhost:3000 |
| **API Documentation** | http://localhost:8200/docs |

---

## 🛠️ Commandes Utiles

```bash
# Voir l'état des services
docker compose ps

# Voir les logs en temps réel
docker compose logs -f

# Arrêter AI Tao
docker compose down

# Redémarrer
docker compose restart
```

---

## 📁 Où sont mes données ?

Toutes vos données sont stockées localement dans :
```
~/.aitao/
├── config/    # Configuration
├── data/      # Base de données
└── logs/      # Journaux
```

---

## ❓ Problèmes Fréquents

**Docker ne démarre pas ?**
→ Ouvrez Docker Desktop, attendez l'icône stable, puis relancez `./install-aitao.sh`

**Port déjà utilisé ?**
→ Modifiez les ports dans le fichier `.env`

**Besoin d'aide ?**
→ Voir les logs : `docker compose logs -f`

---

*AI Tao - Vos données restent sur votre Mac* 🔒
