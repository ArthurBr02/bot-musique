"""Lecteur audio pour un serveur Discord"""

import asyncio
import logging
import time
from typing import Optional
import discord

from bot.audio.track import Track
from bot.audio.queue import MusicQueue
from bot.audio.sources.youtube import YouTubeSource
from bot.audio.sources.spotify import SpotifySource
from bot.config import Config
from bot.utils.exceptions import (
    ConnectionTimeout,
    BotNotConnected,
    InvalidVolume
)

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
        self.spotify_source = SpotifySource()
        # Position tracking for pause/resume
        self._playback_start_time: Optional[float] = None
        self._pause_position: float = 0.0
        # Activity tracking for auto-disconnect
        self._last_activity_time: Optional[float] = time.time()
        # Stream URL tracking for refresh
        self._stream_url_time: Optional[float] = None
        self._current_stream_url: Optional[str] = None
        # Monitoring task for stream health
        self._monitor_task: Optional[asyncio.Task] = None
    
    async def connect(self, channel: discord.VoiceChannel, timeout: int = None) -> bool:
        """
        Connecte le bot à un canal vocal
        
        Args:
            channel: Canal vocal à rejoindre
            timeout: Timeout de connexion en secondes (défaut: Config.CONNECTION_TIMEOUT)
            
        Returns:
            True si connexion réussie
            
        Raises:
            ConnectionTimeout: Si la connexion prend trop de temps
        """
        if timeout is None:
            timeout = Config.CONNECTION_TIMEOUT
        
        try:
            if self.voice_client and self.voice_client.is_connected():
                # Déjà connecté, déplacer vers le nouveau canal
                await asyncio.wait_for(
                    self.voice_client.move_to(channel),
                    timeout=timeout
                )
            else:
                self.voice_client = await asyncio.wait_for(
                    channel.connect(),
                    timeout=timeout
                )
            
            logger.info(f"Connecté au canal vocal: {channel.name} ({self.guild.name})")
            
            # Mettre à jour l'activité
            self._update_activity()
            
            # Démarrer la boucle de lecture si pas déjà démarrée
            if not self._player_task or self._player_task.done():
                self._player_task = asyncio.create_task(self._player_loop())
            
            return True
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout lors de la connexion au canal vocal: {channel.name}")
            raise ConnectionTimeout()
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
            
            # Annuler la tâche de monitoring
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
            
            # Déconnecter
            if self.voice_client:
                await self.voice_client.disconnect()
                self.voice_client = None
            
            # Nettoyer la queue et réinitialiser l'état
            await self.queue.clear()
            self.current = None
            self._is_playing = False
            self._playback_start_time = None
            self._pause_position = 0.0
            self._last_activity_time = None
            
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
        self._update_activity()
        logger.info(f"Piste ajoutée: {track.title} (position {position})")
        return position
    
    async def stop(self) -> None:
        """Arrête la lecture et vide la queue"""
        await self.queue.clear()
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()
        self.current = None
        self._is_playing = False
        # Réinitialiser le suivi de position
        self._playback_start_time = None
        self._pause_position = 0.0
        # Réinitialiser le suivi du stream
        self._stream_url_time = None
        self._current_stream_url = None
        logger.info("Lecture arrêtée")
    
    async def clear_queue(self) -> None:
        """Vide la queue sans arrêter la lecture en cours"""
        await self.queue.clear()
        self._update_activity()
        logger.info("Queue vidée")
    
    async def pause(self) -> bool:
        """
        Met en pause la lecture et sauvegarde la position actuelle
        
        Returns:
            True si pause réussie, False sinon
        """
        if self.voice_client and self.voice_client.is_playing():
            # Calculer la position actuelle avant de mettre en pause
            if self._playback_start_time is not None:
                elapsed = time.time() - self._playback_start_time
                self._pause_position += elapsed
                logger.info(f"Pause à la position: {self._pause_position:.2f} secondes")
            
            self.voice_client.pause()
            self._update_activity()
            logger.info("Lecture en pause")
            return True
        return False
    
    async def resume(self) -> bool:
        """
        Reprend la lecture en régénérant l'URL du stream
        Reprend à la position exacte où la lecture a été mise en pause
        
        Returns:
            True si reprise réussie, False sinon
        """
        if not self.voice_client or not self.voice_client.is_paused():
            return False
        
        if not self.current:
            return False
        
        try:
            # Arrêter la lecture actuelle
            self.voice_client.stop()
            
            # Régénérer l'URL du stream pour éviter l'expiration
            logger.info(f"Régénération de l'URL pour reprise: {self.current.title}")
            stream_url = await self.youtube_source.get_fresh_stream_url(self.current)
            
            if not stream_url:
                logger.error(f"Impossible de régénérer l'URL pour: {self.current.title}")
                return False
            
            # Créer une nouvelle source audio avec l'URL fraîche et la position de reprise
            logger.info(f"Reprise à la position: {self._pause_position:.2f} secondes")
            audio_source = YouTubeSource.create_audio_source(stream_url, self._pause_position)
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=self.volume)
            
            # Créer un événement pour la fin de lecture
            playback_finished = asyncio.Event()
            
            def after_playback(error):
                if error:
                    logger.error(f"Erreur de lecture après reprise: {error}")
                playback_finished.set()
            
            # Relancer la lecture avec la nouvelle source
            self.voice_client.play(audio_source, after=after_playback)
            
            # Réinitialiser le temps de départ pour le suivi de position
            self._playback_start_time = time.time()
            # Mettre à jour le tracking de l'URL du stream
            self._stream_url_time = time.time()
            self._current_stream_url = stream_url
            self._update_activity()
            
            logger.info(f"Lecture reprise avec URL fraîche: {self.current.title}")
            return True
            
        except Exception as e:
            logger.error(
                f"Erreur lors de la reprise: {e}",
                exc_info=True  # Inclut la stack trace complète
            )
            logger.error(
                f"État du voice_client: "
                f"connected={self.voice_client.is_connected() if self.voice_client else False}, "
                f"playing={self.voice_client.is_playing() if self.voice_client else False}, "
                f"paused={self.voice_client.is_paused() if self.voice_client else False}, "
                f"Piste: {self.current.title if self.current else 'None'}"
            )
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
            self._update_activity()
            logger.info("Piste passée")
            return True
        return False
    
    def set_volume(self, volume: float) -> None:
        """
        Règle le volume (0.0 à 1.0)
        
        Args:
            volume: Niveau de volume (0.0 à 1.0)
            
        Raises:
            InvalidVolume: Si le volume est hors limites
        """
        if not 0.0 <= volume <= 1.0:
            raise InvalidVolume(volume * 100)
        
        self.volume = volume
        if self.voice_client and self.voice_client.source:
            self.voice_client.source.volume = self.volume
        self._update_activity()
        logger.info(f"Volume réglé à {int(self.volume * 100)}%")
    
    def is_playing(self) -> bool:
        """Vérifie si le player est en train de jouer"""
        return self._is_playing and self.voice_client and self.voice_client.is_playing()
    
    def is_connected(self) -> bool:
        """Vérifie si le bot est connecté à un canal vocal"""
        return self.voice_client is not None and self.voice_client.is_connected()
    
    def get_current_position(self) -> float:
        """
        Retourne la position actuelle de lecture en secondes
        Utile pour le débogage et les futures fonctionnalités (barre de progression, etc.)
        
        Returns:
            Position en secondes
        """
        if not self._is_playing or self._playback_start_time is None:
            return self._pause_position
        
        # Calculer la position actuelle = position de pause + temps écoulé depuis la reprise
        elapsed = time.time() - self._playback_start_time
        return self._pause_position + elapsed
    
    def _update_activity(self) -> None:
        """Met à jour le timestamp de la dernière activité"""
        self._last_activity_time = time.time()
    
    def _check_inactivity(self) -> bool:
        """
        Vérifie si le timeout d'inactivité est dépassé
        
        Returns:
            True si inactif depuis trop longtemps, False sinon
        """
        if self._last_activity_time is None:
            return False
        
        inactive_time = time.time() - self._last_activity_time
        return inactive_time >= Config.INACTIVITY_TIMEOUT
    
    def _should_refresh_stream_url(self) -> bool:
        """
        Vérifie si l'URL du stream doit être rafraîchie
        Les URLs YouTube expirent généralement après 6 heures
        On rafraîchit après 4 heures pour avoir une marge
        
        Returns:
            True si l'URL doit être rafraîchie
        """
        if self._stream_url_time is None:
            return False
        
        stream_age = time.time() - self._stream_url_time
        # Rafraîchir après 4 heures (14400 secondes)
        return stream_age >= 14400
    
    async def _refresh_stream_url(self) -> bool:
        """
        Rafraîchit l'URL du stream pendant la lecture
        Utilisé pour éviter l'expiration des URLs YouTube
        
        Returns:
            True si le rafraîchissement a réussi
        """
        if not self.current or not self.voice_client or not self.voice_client.is_playing():
            return False
        
        try:
            # Sauvegarder la position actuelle
            current_position = self.get_current_position()
            
            logger.info(f"Rafraîchissement de l'URL du stream pour: {self.current.title} (position: {current_position:.1f}s)")
            
            # Obtenir une nouvelle URL
            stream_url = await self.youtube_source.get_fresh_stream_url(self.current)
            
            if not stream_url:
                logger.error(f"Impossible de rafraîchir l'URL pour: {self.current.title}")
                return False
            
            # Arrêter la lecture actuelle
            self.voice_client.stop()
            await asyncio.sleep(0.2)
            
            # Créer une nouvelle source audio à partir de la position actuelle
            audio_source = YouTubeSource.create_audio_source(stream_url, current_position)
            audio_source = discord.PCMVolumeTransformer(audio_source, volume=self.volume)
            
            # Créer un événement pour la fin de lecture
            playback_finished = asyncio.Event()
            
            def after_playback(error):
                if error:
                    logger.error(f"Erreur de lecture après rafraîchissement: {error}")
                playback_finished.set()
            
            # Relancer la lecture
            self.voice_client.play(audio_source, after=after_playback)
            
            # Mettre à jour le tracking
            self._playback_start_time = time.time()
            self._pause_position = current_position
            self._stream_url_time = time.time()
            self._current_stream_url = stream_url
            
            logger.info(f"Stream URL rafraîchi avec succès pour: {self.current.title}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement du stream: {e}", exc_info=True)
            return False
    
    async def _stream_monitor_loop(self) -> None:
        """
        Boucle de monitoring qui vérifie la santé du stream
        et rafraîchit l'URL si nécessaire
        """
        logger.info("Boucle de monitoring du stream démarrée")
        
        try:
            while True:
                await asyncio.sleep(60)  # Vérifier toutes les minutes
                
                # Vérifier si on doit rafraîchir l'URL
                if self._should_refresh_stream_url() and self._is_playing:
                    logger.info("L'URL du stream a besoin d'être rafraîchie (4h)")
                    await self._refresh_stream_url()
                
        except asyncio.CancelledError:
            logger.info("Boucle de monitoring arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de monitoring: {e}")
    
    async def _player_loop(self) -> None:
        """Boucle principale de lecture audio"""
        logger.info("Boucle de lecture démarrée")
        
        # Démarrer la boucle de monitoring
        if not self._monitor_task or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._stream_monitor_loop())
        
        try:
            while True:
                # Vérifier l'inactivité
                if self._check_inactivity():
                    logger.info(f"Déconnexion par inactivité ({Config.INACTIVITY_TIMEOUT}s) - {self.guild.name}")
                    await self.disconnect()
                    break
                
                # Attendre qu'une piste soit disponible
                while await self.queue.is_empty():
                    self._is_playing = False
                    # Vérifier l'inactivité pendant l'attente
                    if self._check_inactivity():
                        logger.info(f"Déconnexion par inactivité ({Config.INACTIVITY_TIMEOUT}s) - {self.guild.name}")
                        await self.disconnect()
                        return
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
                        # Vérifier l'état du voice_client avant de jouer
                        if self.voice_client.is_playing():
                            logger.warning(
                                f"Le voice_client est déjà en train de jouer. "
                                f"État: is_playing={self.voice_client.is_playing()}, "
                                f"is_paused={self.voice_client.is_paused()}, "
                                f"Piste actuelle: {self.current.title if self.current else 'None'}, "
                                f"Nouvelle piste: {track.title}"
                            )
                            # Arrêter la lecture actuelle avant de continuer
                            self.voice_client.stop()
                            # Attendre un peu pour que l'arrêt soit effectif
                            await asyncio.sleep(0.2)
                        
                        self._is_playing = True
                        
                        # Initialiser le temps de départ et réinitialiser la position de pause
                        self._playback_start_time = time.time()
                        self._pause_position = 0.0
                        # Mettre à jour le tracking de l'URL du stream
                        self._stream_url_time = time.time()
                        self._current_stream_url = stream_url
                        self._update_activity()
                        
                        logger.info(
                            f"Démarrage de la lecture: {track.title} "
                            f"(État: is_playing={self.voice_client.is_playing()}, "
                            f"is_paused={self.voice_client.is_paused()})"
                        )
                        
                        self.voice_client.play(audio_source, after=after_playback)
                        logger.info(f"Lecture en cours: {track.title}")
                        
                        # Attendre la fin de la lecture
                        await playback_finished.wait()
                        
                        # Si loop activé et pas de skip, remettre la piste dans la queue
                        if self.loop and not self._skip_requested:
                            await self.queue.add(track)
                    
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la lecture de {track.title}: {e}",
                        exc_info=True  # Inclut la stack trace complète
                    )
                    logger.error(
                        f"État du voice_client: "
                        f"connected={self.voice_client.is_connected() if self.voice_client else False}, "
                        f"playing={self.voice_client.is_playing() if self.voice_client else False}, "
                        f"paused={self.voice_client.is_paused() if self.voice_client else False}"
                    )
                    continue
                
                finally:
                    # Petit délai entre les pistes
                    await asyncio.sleep(0.5)
        
        except asyncio.CancelledError:
            logger.info("Boucle de lecture arrêtée")
        except Exception as e:
            logger.error(f"Erreur dans la boucle de lecture: {e}")
