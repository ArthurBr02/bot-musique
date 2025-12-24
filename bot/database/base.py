"""Interface abstraite pour la base de données"""

from abc import ABC, abstractmethod
from typing import List, Optional
from bot.database.models import Playlist, PlaylistTrack
from bot.audio.track import Track


class DatabaseInterface(ABC):
    """Interface abstraite pour la persistance des playlists"""
    
    @abstractmethod
    async def init(self) -> None:
        """Initialise la base de données (création des tables, etc.)"""
        pass
    
    @abstractmethod
    async def create_playlist(self, name: str, guild_id: int, owner_id: int) -> Playlist:
        """
        Crée une nouvelle playlist vide
        
        Args:
            name: Nom de la playlist
            guild_id: ID du serveur Discord
            owner_id: ID du membre créateur
            
        Returns:
            Playlist créée avec son ID
        """
        pass
    
    @abstractmethod
    async def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """
        Récupère une playlist par son ID
        
        Args:
            playlist_id: ID de la playlist
            
        Returns:
            Playlist ou None si non trouvée
        """
        pass
    
    @abstractmethod
    async def get_playlist_by_name(self, name: str, guild_id: int) -> Optional[Playlist]:
        """
        Récupère une playlist par son nom dans un serveur
        
        Args:
            name: Nom de la playlist
            guild_id: ID du serveur
            
        Returns:
            Playlist ou None si non trouvée
        """
        pass
    
    @abstractmethod
    async def get_playlists_by_guild(self, guild_id: int) -> List[Playlist]:
        """
        Récupère toutes les playlists d'un serveur
        
        Args:
            guild_id: ID du serveur
            
        Returns:
            Liste des playlists
        """
        pass
    
    @abstractmethod
    async def delete_playlist(self, playlist_id: int) -> bool:
        """
        Supprime une playlist
        
        Args:
            playlist_id: ID de la playlist
            
        Returns:
            True si suppression réussie, False sinon
        """
        pass
    
    @abstractmethod
    async def add_track_to_playlist(self, playlist_id: int, track: Track) -> bool:
        """
        Ajoute une piste à une playlist
        
        Args:
            playlist_id: ID de la playlist
            track: Piste à ajouter
            
        Returns:
            True si ajout réussi, False sinon
        """
        pass
    
    @abstractmethod
    async def remove_track_from_playlist(self, playlist_id: int, position: int) -> bool:
        """
        Retire une piste d'une playlist par sa position
        
        Args:
            playlist_id: ID de la playlist
            position: Position de la piste (1-indexed)
            
        Returns:
            True si suppression réussie, False sinon
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Ferme la connexion à la base de données"""
        pass
