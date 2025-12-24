"""Configuration du bot Discord"""

import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class Config:
    """Configuration centralisée du bot"""
    
    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    
    # Guilds de test pour sync instantané des commandes (optionnel)
    # Format: IDs séparés par des virgules, ex: "123456789,987654321"
    TEST_GUILDS: list[int] = [
        int(guild_id.strip()) 
        for guild_id in os.getenv("TEST_GUILDS", "").split(",") 
        if guild_id.strip()
    ]
    
    # YouTube
    YT_DLP_OPTIONS = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
    }
    
    # Spotify (optionnel)
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
    
    # Audio
    DEFAULT_VOLUME: float = 0.5
    MAX_QUEUE_SIZE: int = 100
    
    # Timeouts (en secondes)
    INACTIVITY_TIMEOUT: int = int(os.getenv("INACTIVITY_TIMEOUT", "300"))  # 5 minutes
    ALONE_TIMEOUT: int = int(os.getenv("ALONE_TIMEOUT", "60"))  # 1 minute
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "10"))  # 10 secondes
    
    # Base de données
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "data/music_bot.db")
    
    # Couleurs pour les embeds Discord
    COLOR_PRIMARY = 0x3498db    # Bleu
    COLOR_SUCCESS = 0x2ecc71    # Vert
    COLOR_ERROR = 0xe74c3c      # Rouge
    COLOR_WARNING = 0xf39c12    # Orange
    COLOR_INFO = 0x95a5a6       # Gris
    
    @classmethod
    def validate(cls) -> bool:
        """Valide que la configuration est correcte"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN manquant dans .env")
        
        if cls.DEFAULT_VOLUME < 0 or cls.DEFAULT_VOLUME > 1:
            raise ValueError("DEFAULT_VOLUME doit être entre 0 et 1")
        
        return True
    @classmethod
    def has_spotify(cls) -> bool:
        """Vérifie si les credentials Spotify sont configurés"""
        return bool(cls.SPOTIFY_CLIENT_ID and cls.SPOTIFY_CLIENT_SECRET)


# Valider la configuration au chargement
Config.validate()
