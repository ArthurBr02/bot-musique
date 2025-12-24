"""Implémentation SQLite de la base de données"""

import aiosqlite
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from bot.database.base import DatabaseInterface
from bot.database.models import Playlist, PlaylistTrack
from bot.audio.track import Track
from bot.config import Config

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseInterface):
    """Implémentation SQLite de la base de données"""
    
    def __init__(self, db_path: str = None):
        """
        Initialise la connexion SQLite
        
        Args:
            db_path: Chemin vers le fichier de base de données
        """
        self.db_path = db_path or Config.DATABASE_PATH
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def init(self) -> None:
        """Initialise la base de données et crée les tables"""
        try:
            # Créer le répertoire si nécessaire
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Ouvrir la connexion
            self.connection = await aiosqlite.connect(self.db_path)
            
            # Créer les tables
            await self._create_tables()
            
            logger.info(f"Base de données initialisée: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise
    
    async def _create_tables(self) -> None:
        """Crée les tables de la base de données"""
        async with self.connection.cursor() as cursor:
            # Table des playlists
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    guild_id INTEGER NOT NULL,
                    owner_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, guild_id)
                )
            """)
            
            # Table des pistes de playlist
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    duration INTEGER DEFAULT 0,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            """)
            
            # Index pour améliorer les performances
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlists_guild 
                ON playlists(guild_id)
            """)
            
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist 
                ON playlist_tracks(playlist_id)
            """)
            
            await self.connection.commit()
    
    async def create_playlist(self, name: str, guild_id: int, owner_id: int) -> Playlist:
        """Crée une nouvelle playlist"""
        async with self.connection.cursor() as cursor:
            try:
                created_at = datetime.now()
                
                await cursor.execute("""
                    INSERT INTO playlists (name, guild_id, owner_id, created_at)
                    VALUES (?, ?, ?, ?)
                """, (name, guild_id, owner_id, created_at))
                
                await self.connection.commit()
                
                playlist_id = cursor.lastrowid
                
                logger.info(f"Playlist créée: {name} (ID: {playlist_id})")
                
                return Playlist(
                    id=playlist_id,
                    name=name,
                    guild_id=guild_id,
                    owner_id=owner_id,
                    created_at=created_at,
                    tracks=[]
                )
                
            except aiosqlite.IntegrityError:
                logger.warning(f"Playlist déjà existante: {name} (guild: {guild_id})")
                raise ValueError(f"Une playlist nommée '{name}' existe déjà sur ce serveur.")
    
    async def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """Récupère une playlist par son ID"""
        async with self.connection.cursor() as cursor:
            # Récupérer la playlist
            await cursor.execute("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE id = ?
            """, (playlist_id,))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            # Récupérer les pistes
            tracks = await self._get_playlist_tracks(playlist_id)
            
            return Playlist(
                id=row[0],
                name=row[1],
                guild_id=row[2],
                owner_id=row[3],
                created_at=datetime.fromisoformat(row[4]),
                tracks=tracks
            )
    
    async def get_playlist_by_name(self, name: str, guild_id: int) -> Optional[Playlist]:
        """Récupère une playlist par son nom"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE name = ? AND guild_id = ?
            """, (name, guild_id))
            
            row = await cursor.fetchone()
            if not row:
                return None
            
            tracks = await self._get_playlist_tracks(row[0])
            
            return Playlist(
                id=row[0],
                name=row[1],
                guild_id=row[2],
                owner_id=row[3],
                created_at=datetime.fromisoformat(row[4]),
                tracks=tracks
            )
    
    async def get_playlists_by_guild(self, guild_id: int) -> List[Playlist]:
        """Récupère toutes les playlists d'un serveur"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE guild_id = ?
                ORDER BY created_at DESC
            """, (guild_id,))
            
            rows = await cursor.fetchall()
            
            playlists = []
            for row in rows:
                tracks = await self._get_playlist_tracks(row[0])
                playlists.append(Playlist(
                    id=row[0],
                    name=row[1],
                    guild_id=row[2],
                    owner_id=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    tracks=tracks
                ))
            
            return playlists
    
    async def delete_playlist(self, playlist_id: int) -> bool:
        """Supprime une playlist"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM playlists WHERE id = ?
            """, (playlist_id,))
            
            await self.connection.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info(f"Playlist supprimée: ID {playlist_id}")
            
            return deleted
    
    async def add_track_to_playlist(self, playlist_id: int, track: Track) -> bool:
        """Ajoute une piste à une playlist"""
        async with self.connection.cursor() as cursor:
            # Trouver la prochaine position
            await cursor.execute("""
                SELECT MAX(position) FROM playlist_tracks
                WHERE playlist_id = ?
            """, (playlist_id,))
            
            max_pos = await cursor.fetchone()
            next_position = (max_pos[0] or 0) + 1
            
            # Insérer la piste
            await cursor.execute("""
                INSERT INTO playlist_tracks (playlist_id, title, url, source, position, duration)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (playlist_id, track.title, track.url, track.source, next_position, track.duration))
            
            await self.connection.commit()
            
            logger.info(f"Piste ajoutée à la playlist {playlist_id}: {track.title}")
            return True
    
    async def remove_track_from_playlist(self, playlist_id: int, position: int) -> bool:
        """Retire une piste d'une playlist"""
        async with self.connection.cursor() as cursor:
            # Supprimer la piste
            await cursor.execute("""
                DELETE FROM playlist_tracks
                WHERE playlist_id = ? AND position = ?
            """, (playlist_id, position))
            
            deleted = cursor.rowcount > 0
            
            if deleted:
                # Réorganiser les positions
                await cursor.execute("""
                    UPDATE playlist_tracks
                    SET position = position - 1
                    WHERE playlist_id = ? AND position > ?
                """, (playlist_id, position))
            
            await self.connection.commit()
            
            if deleted:
                logger.info(f"Piste retirée de la playlist {playlist_id} à la position {position}")
            
            return deleted
    
    async def _get_playlist_tracks(self, playlist_id: int) -> List[PlaylistTrack]:
        """Récupère toutes les pistes d'une playlist"""
        async with self.connection.cursor() as cursor:
            await cursor.execute("""
                SELECT id, playlist_id, title, url, source, position, duration
                FROM playlist_tracks
                WHERE playlist_id = ?
                ORDER BY position ASC
            """, (playlist_id,))
            
            rows = await cursor.fetchall()
            
            return [
                PlaylistTrack(
                    id=row[0],
                    playlist_id=row[1],
                    title=row[2],
                    url=row[3],
                    source=row[4],
                    position=row[5],
                    duration=row[6]
                )
                for row in rows
            ]
    
    async def close(self) -> None:
        """Ferme la connexion à la base de données"""
        if self.connection:
            await self.connection.close()
            logger.info("Connexion à la base de données fermée")
