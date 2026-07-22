"""Implémentation PostgreSQL de la base de données"""

import asyncpg
import logging
from datetime import datetime
from typing import List, Optional

from bot.database.base import DatabaseInterface
from bot.database.models import Playlist, PlaylistTrack, AITemplate, ConversationMessage
from bot.audio.track import Track
from bot.config import Config

logger = logging.getLogger(__name__)


class PostgresDatabase(DatabaseInterface):
    """Implémentation PostgreSQL de la base de données"""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        database: str = None,
    ):
        """
        Initialise la configuration de connexion PostgreSQL

        Args:
            host: Hôte du serveur PostgreSQL
            port: Port du serveur PostgreSQL
            user: Utilisateur de la base de données
            password: Mot de passe de l'utilisateur
            database: Nom de la base de données
        """
        self.host = host or Config.DB_HOST
        self.port = port or Config.DB_PORT
        self.user = user or Config.DB_USER
        self.password = password if password is not None else Config.DB_PASSWORD
        self.database = database or Config.DB_NAME
        self.pool: Optional[asyncpg.Pool] = None

    async def init(self) -> None:
        """Initialise le pool de connexions et crée les tables"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
            )

            await self._create_tables()

            logger.info(
                f"Base de données initialisée: {self.host}:{self.port}/{self.database}"
            )

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")
            raise

    async def _create_tables(self) -> None:
        """Crée les tables de la base de données"""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    guild_id BIGINT NOT NULL,
                    owner_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, guild_id)
                );

                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id BIGSERIAL PRIMARY KEY,
                    playlist_id BIGINT NOT NULL,
                    title TEXT NOT NULL,
                    url TEXT NOT NULL,
                    source TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    duration INTEGER DEFAULT 0,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_playlists_guild
                ON playlists(guild_id);

                CREATE INDEX IF NOT EXISTS idx_playlist_tracks_playlist
                ON playlist_tracks(playlist_id);

                CREATE TABLE IF NOT EXISTS ai_templates (
                    id BIGSERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    name TEXT NOT NULL,
                    system_prompt TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, guild_id)
                );

                CREATE TABLE IF NOT EXISTS conversation_history (
                    id BIGSERIAL PRIMARY KEY,
                    guild_id BIGINT NOT NULL,
                    channel_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_ai_templates_guild
                ON ai_templates(guild_id);

                CREATE INDEX IF NOT EXISTS idx_ai_templates_active
                ON ai_templates(guild_id, is_active);

                CREATE INDEX IF NOT EXISTS idx_conversation_guild_channel
                ON conversation_history(guild_id, channel_id, timestamp);
            """)

    async def create_playlist(self, name: str, guild_id: int, owner_id: int) -> Playlist:
        """Crée une nouvelle playlist"""
        async with self.pool.acquire() as conn:
            try:
                created_at = datetime.now()

                playlist_id = await conn.fetchval("""
                    INSERT INTO playlists (name, guild_id, owner_id, created_at)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                """, name, guild_id, owner_id, created_at)

                logger.info(f"Playlist créée: {name} (ID: {playlist_id})")

                return Playlist(
                    id=playlist_id,
                    name=name,
                    guild_id=guild_id,
                    owner_id=owner_id,
                    created_at=created_at,
                    tracks=[]
                )

            except asyncpg.UniqueViolationError:
                logger.warning(f"Playlist déjà existante: {name} (guild: {guild_id})")
                raise ValueError(f"Une playlist nommée '{name}' existe déjà sur ce serveur.")

    async def get_playlist(self, playlist_id: int) -> Optional[Playlist]:
        """Récupère une playlist par son ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE id = $1
            """, playlist_id)

            if not row:
                return None

            tracks = await self._get_playlist_tracks(playlist_id)

            return Playlist(
                id=row["id"],
                name=row["name"],
                guild_id=row["guild_id"],
                owner_id=row["owner_id"],
                created_at=row["created_at"],
                tracks=tracks
            )

    async def get_playlist_by_name(self, name: str, guild_id: int) -> Optional[Playlist]:
        """Récupère une playlist par son nom"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE name = $1 AND guild_id = $2
            """, name, guild_id)

            if not row:
                return None

            tracks = await self._get_playlist_tracks(row["id"])

            return Playlist(
                id=row["id"],
                name=row["name"],
                guild_id=row["guild_id"],
                owner_id=row["owner_id"],
                created_at=row["created_at"],
                tracks=tracks
            )

    async def get_playlists_by_guild(self, guild_id: int) -> List[Playlist]:
        """Récupère toutes les playlists d'un serveur"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, guild_id, owner_id, created_at
                FROM playlists
                WHERE guild_id = $1
                ORDER BY created_at DESC
            """, guild_id)

            playlists = []
            for row in rows:
                tracks = await self._get_playlist_tracks(row["id"])
                playlists.append(Playlist(
                    id=row["id"],
                    name=row["name"],
                    guild_id=row["guild_id"],
                    owner_id=row["owner_id"],
                    created_at=row["created_at"],
                    tracks=tracks
                ))

            return playlists

    async def delete_playlist(self, playlist_id: int) -> bool:
        """Supprime une playlist"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM playlists WHERE id = $1
            """, playlist_id)

            deleted = result != "DELETE 0"
            if deleted:
                logger.info(f"Playlist supprimée: ID {playlist_id}")

            return deleted

    async def add_track_to_playlist(self, playlist_id: int, track: Track) -> bool:
        """Ajoute une piste à une playlist"""
        async with self.pool.acquire() as conn:
            max_pos = await conn.fetchval("""
                SELECT MAX(position) FROM playlist_tracks
                WHERE playlist_id = $1
            """, playlist_id)

            next_position = (max_pos or 0) + 1

            await conn.execute("""
                INSERT INTO playlist_tracks (playlist_id, title, url, source, position, duration)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, playlist_id, track.title, track.url, track.source, next_position, track.duration)

            logger.info(f"Piste ajoutée à la playlist {playlist_id}: {track.title}")
            return True

    async def remove_track_from_playlist(self, playlist_id: int, position: int) -> bool:
        """Retire une piste d'une playlist"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute("""
                    DELETE FROM playlist_tracks
                    WHERE playlist_id = $1 AND position = $2
                """, playlist_id, position)

                deleted = result != "DELETE 0"

                if deleted:
                    # Réorganiser les positions
                    await conn.execute("""
                        UPDATE playlist_tracks
                        SET position = position - 1
                        WHERE playlist_id = $1 AND position > $2
                    """, playlist_id, position)

            if deleted:
                logger.info(f"Piste retirée de la playlist {playlist_id} à la position {position}")

            return deleted

    async def _get_playlist_tracks(self, playlist_id: int) -> List[PlaylistTrack]:
        """Récupère toutes les pistes d'une playlist"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, playlist_id, title, url, source, position, duration
                FROM playlist_tracks
                WHERE playlist_id = $1
                ORDER BY position ASC
            """, playlist_id)

            return [
                PlaylistTrack(
                    id=row["id"],
                    playlist_id=row["playlist_id"],
                    title=row["title"],
                    url=row["url"],
                    source=row["source"],
                    position=row["position"],
                    duration=row["duration"]
                )
                for row in rows
            ]

    # ==================== AI Template Methods ====================

    async def get_active_template(self, guild_id: int) -> Optional[AITemplate]:
        """Récupère le template IA actif pour un serveur"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, guild_id, name, system_prompt, is_active, created_at, updated_at
                FROM ai_templates
                WHERE guild_id = $1 AND is_active = TRUE
                LIMIT 1
            """, guild_id)

            if not row:
                return None

            return AITemplate(
                id=row["id"],
                guild_id=row["guild_id"],
                name=row["name"],
                system_prompt=row["system_prompt"],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )

    async def get_all_templates(self, guild_id: int) -> List[AITemplate]:
        """Récupère tous les templates IA d'un serveur"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, guild_id, name, system_prompt, is_active, created_at, updated_at
                FROM ai_templates
                WHERE guild_id = $1
                ORDER BY created_at DESC
            """, guild_id)

            return [
                AITemplate(
                    id=row["id"],
                    guild_id=row["guild_id"],
                    name=row["name"],
                    system_prompt=row["system_prompt"],
                    is_active=row["is_active"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"]
                )
                for row in rows
            ]

    async def save_template(self, template: AITemplate) -> AITemplate:
        """Sauvegarde ou met à jour un template IA"""
        async with self.pool.acquire() as conn:
            try:
                template.updated_at = datetime.now()

                if template.id is None:
                    # Nouveau template
                    template.id = await conn.fetchval("""
                        INSERT INTO ai_templates (guild_id, name, system_prompt, is_active, created_at, updated_at)
                        VALUES ($1, $2, $3, $4, $5, $6)
                        RETURNING id
                    """,
                        template.guild_id,
                        template.name,
                        template.system_prompt,
                        template.is_active,
                        template.created_at,
                        template.updated_at
                    )

                    logger.info(f"Template IA créé: {template.name} (ID: {template.id})")
                else:
                    # Mise à jour
                    await conn.execute("""
                        UPDATE ai_templates
                        SET system_prompt = $1, is_active = $2, updated_at = $3
                        WHERE id = $4
                    """, template.system_prompt, template.is_active, template.updated_at, template.id)

                    logger.info(f"Template IA mis à jour: {template.name} (ID: {template.id})")

                return template

            except asyncpg.UniqueViolationError:
                logger.warning(f"Template déjà existant: {template.name} (guild: {template.guild_id})")
                raise ValueError(f"Un template nommé '{template.name}' existe déjà sur ce serveur.")

    async def delete_template(self, template_id: int) -> bool:
        """Supprime un template IA"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM ai_templates WHERE id = $1
            """, template_id)

            deleted = result != "DELETE 0"
            if deleted:
                logger.info(f"Template IA supprimé: ID {template_id}")

            return deleted

    async def set_active_template(self, guild_id: int, template_id: int) -> bool:
        """Définit le template actif pour un serveur"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Désactiver tous les templates du serveur
                await conn.execute("""
                    UPDATE ai_templates
                    SET is_active = FALSE
                    WHERE guild_id = $1
                """, guild_id)

                # Activer le template spécifié
                result = await conn.execute("""
                    UPDATE ai_templates
                    SET is_active = TRUE, updated_at = $1
                    WHERE id = $2 AND guild_id = $3
                """, datetime.now(), template_id, guild_id)

            activated = result != "UPDATE 0"
            if activated:
                logger.info(f"Template IA activé: ID {template_id} pour guild {guild_id}")

            return activated

    # ==================== Conversation History Methods ====================

    async def get_conversation_history(
        self,
        guild_id: int,
        channel_id: int,
        limit: int = 50
    ) -> List[ConversationMessage]:
        """Récupère l'historique de conversation pour un canal"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, guild_id, channel_id, user_id, role, content, timestamp
                FROM conversation_history
                WHERE guild_id = $1 AND channel_id = $2
                ORDER BY timestamp DESC
                LIMIT $3
            """, guild_id, channel_id, limit)

            # Inverser pour avoir du plus ancien au plus récent
            messages = [
                ConversationMessage(
                    id=row["id"],
                    guild_id=row["guild_id"],
                    channel_id=row["channel_id"],
                    user_id=row["user_id"],
                    role=row["role"],
                    content=row["content"],
                    timestamp=row["timestamp"]
                )
                for row in reversed(rows)
            ]

            return messages

    async def save_message(self, message: ConversationMessage) -> ConversationMessage:
        """Sauvegarde un message de conversation"""
        async with self.pool.acquire() as conn:
            message.id = await conn.fetchval("""
                INSERT INTO conversation_history (guild_id, channel_id, user_id, role, content, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id
            """,
                message.guild_id,
                message.channel_id,
                message.user_id,
                message.role,
                message.content,
                message.timestamp
            )

            return message

    async def clear_conversation_history(self, guild_id: int, channel_id: int) -> bool:
        """Efface l'historique de conversation pour un canal"""
        async with self.pool.acquire() as conn:
            result = await conn.execute("""
                DELETE FROM conversation_history
                WHERE guild_id = $1 AND channel_id = $2
            """, guild_id, channel_id)

            deleted = result != "DELETE 0"
            if deleted:
                logger.info(f"Historique effacé pour guild {guild_id}, channel {channel_id}")

            return deleted

    async def close(self) -> None:
        """Ferme le pool de connexions à la base de données"""
        if self.pool:
            await self.pool.close()
            logger.info("Connexion à la base de données fermée")
