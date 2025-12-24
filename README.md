# Bot Discord Musical - ba-tbot-v2

Bot Discord en Python permettant de diffuser de la musique depuis YouTube et Spotify dans des canaux vocaux, avec gestion de playlists et support multi-serveur.

## 🎵 Fonctionnalités

- ✅ Lecture de musique depuis YouTube
- ✅ Support des playlists YouTube
- ✅ Intégration Spotify (conversion vers YouTube)
- ✅ Gestion de playlists personnalisées (sauvegarde/chargement)
- ✅ Support multi-serveur simultané
- ✅ Commandes de contrôle (play, pause, skip, stop, etc.)
- ✅ File d'attente de musique
- ✅ Réglage du volume

## 📋 Prérequis

- Python 3.8 ou supérieur
- FFmpeg installé et accessible dans le PATH
- Un bot Discord (token requis)
- Credentials Spotify (optionnel)

### Installation de FFmpeg

**Windows:**
```bash
choco install ffmpeg
```
Ou téléchargement manuel depuis [ffmpeg.org](https://ffmpeg.org/)

**Linux:**
```bash
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

## 🚀 Installation

1. **Cloner le repository**
```bash
git clone <repository_url>
cd ba-tbot-v2
```

2. **Créer un environnement virtuel**
```bash
python -m venv venv
```

3. **Activer l'environnement virtuel**

Windows:
```bash
venv\Scripts\activate
```

Linux/macOS:
```bash
source venv/bin/activate
```

4. **Installer les dépendances**
```bash
pip install -r requirements.txt
```

5. **Configurer les variables d'environnement**

Copier `.env.example` vers `.env` et remplir les valeurs:
```bash
cp .env.example .env
```

Éditer le fichier `.env`:
```env
DISCORD_TOKEN=votre_token_discord_ici
SPOTIFY_CLIENT_ID=votre_client_id_spotify  # Optionnel
SPOTIFY_CLIENT_SECRET=votre_client_secret_spotify  # Optionnel
```

## 🎮 Utilisation

### Démarrer le bot

```bash
python run.py
```

### Commandes disponibles

| Commande | Description |
|----------|-------------|
| `!play <url/recherche>` | Joue une musique ou l'ajoute à la queue |
| `!pause` | Met en pause la lecture |
| `!resume` | Reprend la lecture |
| `!skip` | Passe à la piste suivante |
| `!stop` | Arrête la lecture et vide la queue |
| `!queue` | Affiche la file d'attente |
| `!nowplaying` | Affiche la piste en cours |
| `!volume <0-100>` | Règle le volume |
| `!save_playlist <nom>` | Sauvegarde la queue actuelle |
| `!load_playlist <nom>` | Charge une playlist |
| `!list_playlists` | Liste les playlists du serveur |
| `!remove_playlist <nom>` | Supprime une playlist |

## 🔧 Configuration Discord

1. Créer une application sur le [Discord Developer Portal](https://discord.com/developers/applications)
2. Créer un Bot et récupérer le token
3. Activer les intents suivants:
   - `GUILDS`
   - `GUILD_VOICE_STATES`
   - `GUILD_MESSAGES`
   - `MESSAGE_CONTENT` (privilégié)
4. Inviter le bot avec les permissions:
   - Connect (se connecter aux vocaux)
   - Speak (jouer de l'audio)
   - Send Messages
   - Embed Links

**URL d'invitation:**
```
https://discord.com/api/oauth2/authorize?client_id=VOTRE_CLIENT_ID&permissions=3165184&scope=bot
```

## 📁 Structure du Projet

```
ba-tbot-v2/
├── bot/
│   ├── __init__.py
│   ├── main.py          # Point d'entrée
│   ├── config.py        # Configuration
│   ├── bot.py           # Classe principale
│   ├── cogs/            # Modules de commandes
│   ├── audio/           # Gestion audio
│   ├── database/        # Persistance
│   └── utils/           # Utilitaires
├── requirements.txt
├── .env.example
└── run.py
```

## 🐛 Dépannage

**Le bot ne se connecte pas:**
- Vérifier que le token Discord est correct dans `.env`
- Vérifier que les intents sont activés sur le Developer Portal

**Pas de son:**
- Vérifier que FFmpeg est installé et dans le PATH
- Vérifier que le bot a les permissions "Connect" et "Speak"

**Erreur lors de la lecture YouTube:**
- Mettre à jour yt-dlp: `pip install --upgrade yt-dlp`

## 📝 Licence

MIT License

## 👨‍💻 Auteur

ba-tbot-v2
