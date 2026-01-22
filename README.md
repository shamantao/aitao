# ☯️ AI Tao

> **L'Intelligence Artificielle Locale, Souveraine et Accessible.**

---

## 1. Philosophie & Manifeste

### Pourquoi AI Tao ?
L'IA moderne est puissante, mais elle est souvent confisquée par le Cloud (perte de confidentialité) ou réservée aux ingénieurs (complexité technique). **AI Tao** est né d'un besoin simple : avoir un assistant personnel capable de tout faire (texte, traduction, vision, code) sur une machine locale (Mac Apple Silicon), sans envoyer un seul octet de donnée à l'extérieur.

### Nos Valeurs
1.  **🔒 Confidentialité Absolue** : "What happens on your Mac, stays on your Mac." Vos documents financiers, vos contrats et votre code ne quittent jamais votre disque dur.
2.  **⚡️ Simplicité Radicale** : L'utilisateur ne doit pas "coder" pour "utiliser". Il dépose un fichier, il pose une question. L'architecture complexe est masquée par une automatisation intelligente.
3.  **🏗 Modularité** : Nous ne réinventons pas la roue. Nous connectons les meilleurs outils (Llama.cpp, AnythingLLM, scripts Python) pour créer un écosystème fluide.

### Cas d'Usage Ciblés
Ce projet est conçu pour être un véritable outil de production au quotidien :
*   **Traductions contextuelles** de documents complexes.
*   **Analyse visuelle (OCR)** : "Lis ce PDF scanné et refais-moi le tableau en Excel".
*   **Vidéo** : Extraction de transcriptions et resynchronisation de sous-titres.
*   **Création** : Génération de logos (SVG) et assistance au codage.

---

## 2. Architecture Technique & Mode d'Emploi

### Le Cœur du Système
L'architecture d'AI Tao est **Hybride**. Elle combine la robustesse de scripts d'automatisation maison avec la convivialité d'interfaces reconnues.

1.  **La Source de Vérité (`config.toml`)** : Tout part de là. On ne configure rien dans l'interface graphique. On définit ses dossiers (`_Volumes`), ses modèles et ses préférences dans ce fichier unique.
2.  **Le Chef d'Orchestre (`aitao.sh`)** : C'est l'exécutable unique. Il lance le moteur d'IA, prépare l'environnement, et lance l'interface utilisateur (AnythingLLM).
3.  **Le "Feeder" (`sync_agent.py` - *En dev*)** : C'est le lien magique. Il lit votre `config.toml` et configure automatiquement l'interface utilisateur (Workspaces, Indexation) pour vous éviter les clics répétitifs.

### Stack Technologique
*   **Langage** : Python 3.14 (Moteur), Bash (Orchestration).
*   **Moteur d'Inférence** : `llama-cpp-python` (Serveur API compatible OpenAI).
*   **Interface (UI)** : Intégration avec **AnythingLLM** (Gestionnaire de connaissances & Chat).
*   **Vector Database** : LanceDB (Intégré).

### Guide de Démarrage Rapide
Pour l'utilisateur, tout doit tenir en une commande :

```bash
# 1. Démarrer tout le système (Moteur + UI + Synchro)
./aitao.sh start

# 2. Vérifier que tout va bien
./aitao.sh status

# 3. Arrêter (Proprement)
./aitao.sh stop
```

Une fois lancé, l'utilisateur ouvre simplement son navigateur sur l'interface (ex: `http://localhost:3001`) et retrouve ses dossiers déjà prêts à l'emploi.

---

## 3. Backlog & Feuille de Route

Cette section liste les fonctionnalités à développer pour atteindre notre vision.

| Fonctionnalité Visée | Implication Technique (Dev) | Priorité |
| :--- | :--- | :--- |
| **Intégration Interface** | Migration vers **AnythingLLM**. Création d'un pont (`sync_agent.py`) pour que nos dossiers locaux soient automatiquement reflétés en Workspaces. | 🔥 Haute |
| **Vision & Tableaux** | Intégration de modèles multimodaux (Llava/Qwen-VL) capables de "voir" un PDF image et d'en extraire la structure JSON/CSV. | 🚀 Moyenne |
| **Vidéo & Suite** | Ajout de `Whisper` (local) dans le pipeline pour transcrire les mp4/mp3 déposés dans un dossier surveillé. | 🔮 Future |
| **Graphisme (SVG)** | Intégration d'un modèle de génération d'image (Flux/SD) ou prompting spécialisé pour code SVG. | 🔮 Future |
| **Installation "Zero-Conf"** | Création d'un setup qui installe Python, Docker (si besoin) et les modèles automatiquement. | 🛡️ Polissage |

---
*© 2026 AI Tao Project - Construit pour les humains, propulsé par le silicium.*
