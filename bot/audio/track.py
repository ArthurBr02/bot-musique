"""Modèle de données pour une piste audio"""

from dataclasses import dataclass
from typing import Optional
import discord


@dataclass
class Track:
    """Représente une piste audio à jouer"""
    
    title: str                      # Titre de la piste
    url: str                        # URL originale (YouTube, Spotify, etc.)
    stream_url: Optional[str]       # URL du stream audio (peut être None jusqu'à l'extraction)
    duration: int                   # Durée en secondes
    thumbnail: str                  # URL de la miniature
    source: str                     # Source: 'youtube' | 'spotify'
    requester: discord.Member       # Membre qui a demandé la piste
    
    def __str__(self) -> str:
        """Représentation textuelle de la piste"""
        minutes, seconds = divmod(self.duration, 60)
        return f"{self.title} [{minutes}:{seconds:02d}]"
    
    @property
    def duration_formatted(self) -> str:
        """Retourne la durée formatée (MM:SS)"""
        minutes, seconds = divmod(self.duration, 60)
        return f"{minutes}:{seconds:02d}"
