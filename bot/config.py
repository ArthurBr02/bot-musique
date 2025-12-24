"""Configuration du bot Discord musical"""

import os
from typing import Optional
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()


class Config:
    """Configuration centralisée du bot"""
    
    # Discord
    DISCORD_TOKEN: str = os.getenv("DISCORD_TOKEN", "")
    COMMAND_PREFIX: str = os.getenv("COMMAND_PREFIX", "!")
    
    # Spotify (optionnel)
    SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
    SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")
    
    # Base de données
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "sqlite")
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "bot_data.db")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Limites et configuration audio
    MAX_QUEUE_SIZE: int = int(os.getenv("MAX_QUEUE_SIZE", "100"))
    DEFAULT_VOLUME: float = float(os.getenv("DEFAULT_VOLUME", "0.5"))
    INACTIVITY_TIMEOUT: int = int(os.getenv("INACTIVITY_TIMEOUT", "300"))  # 5 minutes
    ALONE_TIMEOUT: int = int(os.getenv("ALONE_TIMEOUT", "60"))  # 1 minute
    CONNECTION_TIMEOUT: int = int(os.getenv("CONNECTION_TIMEOUT", "10"))  # 10 secondes
    
    # Couleurs pour les embeds Discord
    COLOR_PRIMARY: int = 0x3498db  # Bleu
    COLOR_SUCCESS: int = 0x2ecc71  # Vert
    COLOR_ERROR: int = 0xe74c3c    # Rouge
    COLOR_WARNING: int = 0xf39c12  # Orange
    COLOR_INFO: int = 0x9b59b6     # Violet
    
    @classmethod
    def validate(cls) -> bool:
        """Valide que la configuration minimale est présente"""
        if not cls.DISCORD_TOKEN:
            raise ValueError("DISCORD_TOKEN est requis dans le fichier .env")
        
        if cls.DEFAULT_VOLUME < 0 or cls.DEFAULT_VOLUME > 1:
            raise ValueError("DEFAULT_VOLUME doit être entre 0 et 1")
        
        return True
    
    @classmethod
    def has_spotify(cls) -> bool:
        """Vérifie si les credentials Spotify sont configurés"""
        return bool(cls.SPOTIFY_CLIENT_ID and cls.SPOTIFY_CLIENT_SECRET)


# Valider la configuration au chargement
Config.validate()
