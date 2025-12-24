# Guide d'utilisation - Chatbot IA Mistral

## Configuration initiale

### 1. Obtenir une clé API Mistral

1. Visitez [https://console.mistral.ai/](https://console.mistral.ai/)
2. Créez un compte ou connectez-vous
3. Générez une clé API
4. Copiez la clé

### 2. Configurer le bot

Ajoutez votre clé API dans le fichier `.env`:

```env
MISTRAL_API_KEY=votre_clé_api_ici
MISTRAL_MODEL=mistral-small-latest
MISTRAL_MAX_TOKENS=1000
MISTRAL_TEMPERATURE=0.7
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Démarrer le bot

```bash
python run.py
```

---

## Commandes disponibles

### Chat avec l'IA

**`/chat <message>`**

Envoie un message au chatbot IA.

**Exemples:**
```
/chat Bonjour! Comment vas-tu?
/chat Explique-moi ce qu'est Python
/chat Raconte-moi une blague
```

**Fonctionnalités:**
- Maintient le contexte de conversation par canal
- Utilise le template actif du serveur
- Gère automatiquement les réponses longues

---

### Gestion des templates

#### Lister les templates

**`/ai_template list`**

Affiche tous les templates configurés pour le serveur.

#### Créer un template

**`/ai_template create <nom> <prompt_système> [activer]`**

Crée un nouveau template de personnalité pour l'IA.

**Exemples:**
```
/ai_template create amical "Tu es un assistant amical et enthousiaste. Utilise des emojis et sois encourageant!" true

/ai_template create technique "Tu es un expert technique. Réponds de manière précise et détaillée avec des exemples de code."

/ai_template create professeur "Tu es un professeur patient. Explique les concepts simplement et pose des questions pour vérifier la compréhension."
```

**Note:** Requiert la permission "Gérer le serveur"

#### Activer un template

**`/ai_template set <nom>`**

Active un template existant.

**Exemple:**
```
/ai_template set technique
```

**Note:** Requiert la permission "Gérer le serveur"

#### Supprimer un template

**`/ai_template delete <nom>`**

Supprime un template.

**Exemple:**
```
/ai_template delete amical
```

**Note:** Requiert la permission "Gérer le serveur"

---

### Gestion de l'historique

**`/ai_clear`**

Efface l'historique de conversation pour le canal actuel. L'IA recommencera avec un contexte vierge.

**Utilisation:**
```
/ai_clear
```

---

## Exemples d'utilisation

### Scénario 1: Assistant de programmation

```
/ai_template create codeur "Tu es un expert en programmation Python. Fournis du code propre et bien commenté avec des explications." true

/chat Comment créer une fonction pour calculer la factorielle?
```

### Scénario 2: Assistant créatif

```
/ai_template create créatif "Tu es un assistant créatif et imaginatif. Aide à générer des idées originales et inspirantes." true

/chat Donne-moi des idées pour un projet Discord bot innovant
```

### Scénario 3: Support technique

```
/ai_template create support "Tu es un agent de support technique patient. Pose des questions pour diagnostiquer les problèmes." true

/chat Mon bot ne se connecte pas à Discord
```

---

## Bonnes pratiques

### Templates efficaces

✅ **Soyez spécifique** - Définissez clairement le rôle et le ton
✅ **Donnez des directives** - Indiquez comment répondre
✅ **Testez et ajustez** - Créez plusieurs templates pour différents usages

❌ **Évitez les prompts vagues** - "Sois utile" n'est pas assez précis
❌ **Ne surchargez pas** - Gardez les prompts concis et clairs

### Gestion de l'historique

- L'historique est conservé par canal
- Utilisez `/ai_clear` pour recommencer une conversation
- L'historique est limité aux 50 derniers messages par défaut

### Multi-serveur

- Chaque serveur a ses propres templates
- Les conversations sont isolées par serveur ET par canal
- Un template peut être actif sur un serveur et inactif sur un autre

---

## Dépannage

### Le bot ne répond pas aux commandes IA

**Vérifiez:**
1. La clé API Mistral est configurée dans `.env`
2. Le package `mistralai` est installé
3. Les logs du bot pour des erreurs

### Erreur "IA n'est pas configurée"

**Solution:**
Ajoutez `MISTRAL_API_KEY` dans votre fichier `.env`

### Réponses lentes

**Causes possibles:**
- Modèle Mistral surchargé
- Connexion internet lente
- Historique de conversation très long

**Solutions:**
- Utilisez `/ai_clear` pour réduire l'historique
- Ajustez `MISTRAL_MAX_TOKENS` dans `.env`

### Erreur de quota API

**Solution:**
Vérifiez votre compte Mistral pour les limites de quota et l'utilisation

---

## Coûts

L'utilisation de l'API Mistral entraîne des coûts basés sur:
- Nombre de tokens envoyés (prompt + historique)
- Nombre de tokens générés (réponse)
- Modèle utilisé

**Recommandations:**
- Utilisez `mistral-small-latest` pour un bon rapport qualité/prix
- Limitez `MISTRAL_MAX_TOKENS` pour contrôler les coûts
- Nettoyez régulièrement l'historique avec `/ai_clear`
- Surveillez votre utilisation sur [console.mistral.ai](https://console.mistral.ai/)
