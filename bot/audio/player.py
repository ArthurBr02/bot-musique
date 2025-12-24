"""Lecteur audio pour un serveur Discord"""

import asyncio
import logging
from typing import Optional
import discord

from bot.audio.track import Track
from bot.audio.queue import MusicQueue
from bot.audio.sources.youtube import YouTubeSource
from bot.config import Config

logger = logging.getLogger(__name__)


class MusicPlayer:
    """Gestionnaire audio pour un serveur Discord"""
    
    def __init__(self, bot, guild: discord.Guild):
        """
        Initialise le player pour un serveur
        
        Args:
            bot: Instance du bot Discord
            guild: Serveur Discord
        """
        self.bot = bot
        self.guild = guild
        self.queue = MusicQueue()
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current: Optional[Track] = None
        self.volume: float = Config.DEFAULT_VOLUME
        self.loop: bool = False
        self._player_task: Optional[asyncio.Task] = None
        self._is_playing = False
        self._skip_requested = False
        self.youtube_source = YouTubeSource()
    
    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """
        Connecte le bot à un canal vocal
        
        Args:
            channel: Canal vocal à rejoindre
            
        Returns:
            True si connexion réussie, False sinon
        """
        try:
            if self.voice_client and self.voice_client.is_connected():
                # Déjà connecté, déplacer vers le nouveau canal
                await self.voice_client.move_to(channel)
            else:
                self.voice_client = await channel.connect()
            
            logger.info(f"Connecté au canal vocal: {channel.name} ({self.guild.name})")
            
            # Démarrer la boucle de lecture si pas déjà démarrée
            if not self._player_task or self._player_task.done():
                self._player_task = asyncio.create_task(self._player_loop())
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la connexion au canal vocal: {e}")
            return False
    
    async def disconnect(self) -> None:
        """Déconnecte le bot du canal vocal et nettoie les ressources"""
        try:
            # Arrêter la lecture
            if self.voice_client and self.voice_client.is_playing():
                self.voice_client.stop()
            
            # Annuler la tâche de lecture
            if self._player_task and not self._player_task.done():
                self._player_task.cancel()
                try:
                    await self._player_task
                except asyncio.CancelledError:
                    pass
            
            # Déconnecter
            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            
            # Nettoyer la queue
            await self.queue.clear()
            self.current = None
            self._is_playing = False
            
            logger.info(f"Déconnecté du canal vocal ({self.guild.name})")
            
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion: {e}")
    
    async def add_track(self, track: Track) -> int:
        """
        Ajoute une piste à la queue
        
        Args:
            track: Piste à ajouter
            
        Returns:
            Position dans la queue
        """
        position = await self.queue.add(track)
        logger.info(f"Piste ajoutée: {track.title} (position {position})")
        return position
    
    async def stop(self) -> None:
        """Arrête la lecture et vide la queue"""
        await self.queue.clear()
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        self.current = None
        self._is_playing = False
        logger.info("Lecture arrêtée")
    
    async def pause(self) -> bool:
        """
        Met en pause la lecture
        
        Returns:
            True si pause réussie, False sinon
        """
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.pause()
            logger.info("Lecture en pause")
            return True
        return False
    
    async def resume(self) -> bool:
        """
        Reprend la lecture
        
        Returns:
            True si reprise réussie, False sinon
        """
        if self.voice_client and self.voice_client.is_paused():
            self.voice_client.resume()
            logger.info("Lecture reprise")
            return True
        return False
    
    async def skip(self) -> bool:
        """
        Passe à la piste suivante
        
        Returns:
            True si skip réussi, False sinon
        """
        if self.voice_client and self.voice_client.is_playing():
            self._skip_requested = True
            self.voice_client.stop()
            logger.info("Piste passée")
            return True
        return False
    
    def set_volume(self, volume: float) -> None:
        """
        Règle le volume (0.0 à 1.0)
        
        Args:
            volume: Niveau de volume (0.0 à 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        if self.voice_client and self.voice_client.source:
            self.voice_client.source.volume = self.volume
        logger.info(f"Volume réglé à {int(self.volume * 100)}%")
    
    def is_playing(self) -> bool:
        """Vérifie si le player est en train de jouer"""
        return self._is_playing and self.voice_client and self.voice_client.is_playing()
    
    def is_connected(self) -> bool:
        """Vérifie si le bot est connecté à un canal vocal"""
        return self.voice_client is not None and self.voice_client.is_connected()
    
    async def _player_loop(self) -> None:
        """Boucle principale de lecture audio"""
        logger.info("Boucle de lecture démarrée")
        
        try:
            while True:
                # Attendre qu'une piste soit disponible
                while await self.queue.is_empty():
                    self._is_playing = False
                    await asyncio.sleep(1)
                
                # Récupérer la prochaine piste
                track = await self.queue.next()
                if not track:
                    continue
                
                self.current = track
                self._skip_requested = False
                
                try:
                    # Toujours régénérer l'URL du stream juste avant la lecture
                    # pour éviter les problèmes d'expiration (URLs YouTube expirent après ~6h)
                    logger.info(f"Régénération de l'URL du stream pour: {track.title}")
                    stream_url = await self.youtube_source.get_fresh_stream_url(track)
                    
                    if not stream_url:
                        logger.error(f"Impossible d'obtenir l'URL du stream pour: {track.title}")
                        continue
                    
                    # Créer la source audio avec l'URL fraîche
                    audio_source = YouTubeSource.create_audio_source(stream_url)
                    audio_source = discord.PCMVolumeTransformer(audio_source, volume=self.volume)
                    
                    # Créer un événement pour attendre la fin de la lecture
                    playback_finished = asyncio.Event()
                    
                    def after_playback(error):
                        """Callback appelé après la fin de la lecture"""
                        if error:
                            logger.error(f"Erreur de lecture: {error}")
                        playback_finished.set()
                    
                    # Lancer la lecture
                    if self.voice_client and self.voice_client.is_connected():
                        self._is_playing = True
                        self.voice_client.play(audio_source, after=after_playback)
                        logger.info(f"Lecture en cours: {track.title}")
                        
                        # Attendre la fin de la lecture
                        await playback_finished.wait()
                        
                        # Si loop activé et pas de skip, remettre la piste dans la queue
                        if self.loop and not self._skip_requested:
                            await self.queue.add(track)
                    
                except Exception as e:
                    logger.error(f"Erreur lors de la lecture de {track.title}: {e}")
                    continue
                
                finally:
                    # Petit délai entre les pistes
                    await asyncio.sleep(0.5)
        
        except asyncio.CancelledError:
            logger.info("Boucle de lecture arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de lecture: {e}")
