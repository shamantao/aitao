# OnlyOffice + AItao — Guide de connexion

Utiliser OnlyOffice comme interface de chat et AItao comme moteur IA local avec RAG.

---

## 1) Démarrer AItao

```bash
./aitao.sh start
```

Vérifier que l'API répond :

```bash
curl http://127.0.0.1:8200/v1/models
```

→ Si la réponse est du JSON avec une liste de modèles, c'est bon.

---

## 2) Indexer vos documents (si pas encore fait)

```bash
./aitao.sh scan run
./aitao.sh queue status   # attendre que la queue soit vide
```

---

## 3) Configurer OnlyOffice

OnlyOffice a deux plugins IA distincts. La configuration diffère légèrement selon lequel tu utilises.

### Plugin classique — AI Assistant (menu Plugins → AI Assistant → ⚙️ → Ajouter un modèle)

| Champ | Valeur |
|---|---|
| Fournisseur | `OpenAI` |
| URL | `http://127.0.0.1:8200/v1` |
| Clé API | `sk-local` |
| Modèle | `llama3.1-context` |

### Plugin sidebar — AI Agent (panneau latéral droit)

| Champ | Valeur |
|---|---|
| Fournisseur | **`OpenAI Compatible`** ← important, pas "OpenAI" |
| Nom | `AItao` (ou ce que tu veux) |
| URL | `http://127.0.0.1:8200/v1` |
| Clé API | `sk-local` |

> Pourquoi **"OpenAI Compatible"** dans le sidebar ?  
> Le type "OpenAI" ne liste que les modèles GPT-5.2 officiels. Nos modèles locaux sont invisibles → badge d'erreur.  
> "OpenAI Compatible" accepte tous les modèles.

---

## 4) Modèles recommandés

| Modèle | Comportement |
|---|---|
| `llama3.1-context` | RAG activé — répond avec ton corpus |
| `llama3.1-basic` | Sans RAG — pour comparaison |
| `qwen-coder-context` | RAG + orienté code |

---

## 5) Dépannage

### "URL invalide"
→ N'utilise pas le fournisseur **Ollama**. Utilise `OpenAI` ou `OpenAI Compatible`.

### "Fournisseur indisponible"

| Cause | Fix |
|---|---|
| Clé API vide | Mets `sk-local` (doit commencer par `sk-`) |
| `localhost` au lieu de `127.0.0.1` | Sur macOS, `localhost` → IPv6 qui ne fonctionne pas |
| Fournisseur "OpenAI" dans le sidebar | Utilise "OpenAI Compatible" à la place |

### "Clé API invalide"

| Cause | Fix |
|---|---|
| URL sans `/v1` (`http://127.0.0.1:8200`) | Ajoute `/v1` → `http://127.0.0.1:8200/v1` |
| Clé ne commence pas par `sk-` | Utilise `sk-local` |

### Vérification rapide
```bash
curl http://127.0.0.1:8200/v1/models          # doit retourner du JSON
curl http://127.0.0.1:8200/api/health         # doit retourner {"status": "ok"}
```

---

## 6) Vérifier que le RAG fonctionne

Pose la même question avec `llama3.1-basic` puis `llama3.1-context`.  
Si `-context` donne des réponses basées sur tes documents → le RAG est actif.

---

## Aide-mémoire

```
AItao démarré ?         ./aitao.sh start
Documents indexés ?     ./aitao.sh scan run
API répond ?            curl http://127.0.0.1:8200/v1/models

OnlyOffice plugin classique  → fournisseur "OpenAI"           + URL .../v1 + clé sk-local
OnlyOffice sidebar AI Agent  → fournisseur "OpenAI Compatible" + URL .../v1 + clé sk-local
```