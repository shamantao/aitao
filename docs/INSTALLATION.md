# Installation d'AiTao 🚀

Bienvenue ! Ce guide vous explique comment installer AiTao en **3 étapes simples**.

---

## ⚙️ Avant de commencer

Pour faire fonctionner AiTao, vous avez besoin d'une seule chose :

### Docker Desktop

Docker Desktop permet à AiTao de fonctionner dans un "conteneur" isolé sur votre ordinateur.

**Installez Docker Desktop selon votre système :**

- **macOS (Apple Silicon M1/M2/M3+)** : https://docs.docker.com/desktop/install/mac-install/
- **Windows 10/11** : https://docs.docker.com/desktop/install/windows-install/
- **Linux** : https://docs.docker.com/desktop/install/linux-install/

> **Après installation :** Redémarrez votre ordinateur et lancez Docker Desktop avant de continuer.

---

## 🚀 Installation en 3 étapes

### Étape 1️⃣ - Décompresser l'archive

1. Téléchargez l'archive AiTao appropriée à votre système :
   - `aitao-macos-arm64.zip` (macOS avec Apple Silicon)
   - `aitao-windows-x64.zip` (Windows 10+)
   - `aitao-linux-x64.zip` (Linux)

2. **Décompressez** l'archive dans un dossier quelconque :
   - **Macintosh :** Double-cliquez sur le fichier ZIP
   - **Windows :** Clic droit → *Extraire tout*
   - **Linux :** `unzip aitao-*.zip`

Vous devriez avoir un dossier contenant :
```
├── install-aitao.sh      (macOS/Linux)
├── install-aitao.bat     (Windows)
├── docker-compose.yml
├── .env.template
└── README.md
```

---

### Étape 2️⃣ - Lancer le script d'installation

Le script `install-aitao` va :
- ✅ Vérifier que Docker est bien installé
- ✅ Créer les dossiers de configuration
- ✅ Télécharger et lancer tous les services

**Sur macOS/Linux :**
```bash
chmod +x install-aitao.sh
./install-aitao.sh
```

**Sur Windows :**
1. Ouvrez **PowerShell** ou **Cmd** en tant qu'administrateur
2. Allez au dossier décompressé : `cd C:\Users\VotreNom\AiTao`
3. Lancez : `install-aitao.bat`

> ⏳ **La première installation prend 3-5 minutes** (téléchargement ~3 GB). C'est normal !

---

### Étape 3️⃣ - Accéder à l'application

Quand l'installation est terminée, un navigateur s'ouvre avec :

**🔗 http://localhost:3000**

Vous pouvez maintenant utiliser AiTao ! 🎉

---

## 🛠️ Problèmes courants

### ❌ "Docker n'est pas installé"

**Solution :**
1. Téléchargez Docker Desktop : https://www.docker.com/products/docker-desktop/
2. Installez-le
3. Redémarrez votre ordinateur
4. Lancez Docker Desktop (vous verrez une petite baleine 🐋)
5. Relancez le script d'installation

---

### ❌ "Docker n'est pas démarré"

**Solution :**
1. Ouvrez **Docker Desktop** depuis votre menu applications
2. Attendez que la baleine 🐋 soit "stable" (quelques secondes)
3. Relancez le script d'installation

---

### ❌ "Le port 8200 (ou 3000) est déjà utilisé"

**Signification :** Un autre programme utilise ce port.

**Solution simple :**
- Arrêtez l'autre application qui utilise ce port
- Redémarrez AiTao

**Pour redémarrer AiTao :**
```bash
# Macintosh/Linux
docker-compose restart

# Windows (PowerShell, dans le dossier décompressé)
docker-compose restart
```

---

### ❌ "La première connexion est lente"

C'est normal ! AiTao télécharge les modèles d'IA la première fois (~2-5 minutes).

Laissez tourner et n'arrêtez pas votre ordinateur. 🌟

---

## 📝 Commandes utiles (optionnel)

Si vous voulez contrôler AiTao manuellement :

```bash
# Voir les logs (pour débuggage)
docker-compose logs -f

# Arrêter AiTao
docker-compose down

# Redémarrer AiTao
docker-compose restart

# Désinstaller complètement (supprime tout)
./uninstall-aitao.sh        # macOS/Linux
uninstall-aitao.bat         # Windows
```

---

## 🆘 Besoin d'aide ?

Si vous avez un problème qui n'est pas listé ici :

1. Vérifiez que **Docker Desktop est lancé** 🐋
2. Essayez d'**arrêter et relancer** : `docker-compose down` puis `docker-compose up -d`
3. Vérifiez votre **connexion Internet** (téléchargement des modèles)

---

**Bon usage ! 🚀**
