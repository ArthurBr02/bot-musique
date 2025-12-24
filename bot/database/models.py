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


@dataclass
class AITemplate:
    """Représente un template de prompt IA pour un serveur"""
    
    id: Optional[int]           # ID dans la base de données (None si pas encore sauvegardé)
    guild_id: int               # ID du serveur Discord
    name: str                   # Nom du template (ex: "default", "friendly", "technical")
    system_prompt: str          # Le prompt système pour l'IA
    is_active: bool = False     # Si ce template est actuellement actif
    created_at: Optional[datetime] = None  # Date de création
    updated_at: Optional[datetime] = None  # Date de dernière modification
    
    def __post_init__(self):
        """Initialisation après création"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class ConversationMessage:
    """Représente un message dans l'historique de conversation"""
    
    id: Optional[int]           # ID dans la base de données (None si pas encore sauvegardé)
    guild_id: int               # ID du serveur Discord
    channel_id: int             # ID du canal Discord
    user_id: int                # ID de l'utilisateur Discord
    role: str                   # Rôle: 'user', 'assistant', 'system'
    content: str                # Contenu du message
    timestamp: Optional[datetime] = None  # Timestamp du message
    
    def __post_init__(self):
        """Initialisation après création"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_api_format(self) -> dict:
        """Convertit le message au format API Mistral"""
        return {
            "role": self.role,
            "content": self.content
        }

