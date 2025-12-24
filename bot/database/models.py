"""Modèles de données pour la base de données"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass
class PlaylistTrack:
    """Représente une piste dans une playlist"""
    
    id: Optional[int]           # ID dans la base de données (None si pas encore sauvegardé)
    playlist_id: int            # ID de la playlist parente
    title: str                  # Titre de la piste
    url: str                    # URL de la piste (YouTube, Spotify, etc.)
    source: str                 # Source: 'youtube' | 'spotify'
    position: int               # Position dans la playlist (1-indexed)
    duration: int = 0           # Durée en secondes


@dataclass
class Playlist:
    """Représente une playlist sauvegardée"""
    
    id: Optional[int]           # ID dans la base de données (None si pas encore sauvegardé)
    name: str                   # Nom de la playlist
    guild_id: int               # ID du serveur Discord
    owner_id: int               # ID du membre qui a créé la playlist
    created_at: datetime        # Date de création
    tracks: List[PlaylistTrack] # Liste des pistes
    
    def __post_init__(self):
        """Initialisation après création"""
        if self.tracks is None:
            self.tracks = []
    
    @property
    def track_count(self) -> int:
        """Retourne le nombre de pistes dans la playlist"""
        return len(self.tracks)
    
    @property
    def total_duration(self) -> int:
        """Retourne la durée totale de la playlist en secondes"""
        return sum(track.duration for track in self.tracks)
    
    @property
    def duration_formatted(self) -> str:
        """Retourne la durée totale formatée (HH:MM:SS)"""
        total = self.total_duration
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"
