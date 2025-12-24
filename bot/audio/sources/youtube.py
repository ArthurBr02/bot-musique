"""Extraction audio depuis YouTube via yt-dlp"""

import asyncio
import logging
from typing import Optional, List, Dict, Any
import discord
import yt_dlp

from bot.audio.track import Track

logger = logging.getLogger(__name__)


class YouTubeSource:
    """Gestionnaire d'extraction audio YouTube"""
    
    # Options pour yt-dlp
    YTDL_OPTIONS = {
        'format': 'bestaudio/best',
        'extractaudio': True,
        'audioformat': 'mp3',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',  # Bind to ipv4 since ipv6 addresses cause issues sometimes
    }
    
    # Options FFmpeg pour discord.py
    FFMPEG_OPTIONS = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }
    
    def __init__(self):
        self.ytdl = yt_dlp.YoutubeDL(self.YTDL_OPTIONS)
    
    async def search(self, query: str, requester: discord.Member) -> Optional[Track]:
        """
        Recherche une vidéo YouTube et retourne un Track
        
        Args:
            query: URL YouTube ou terme de recherche
            requester: Membre Discord qui a fait la demande
            
        Returns:
            Track ou None si non trouvé
        """
        try:
            # Exécuter la recherche dans un thread séparé pour ne pas bloquer
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(query, download=False)
            )
            
            if data is None:
                logger.warning(f"Aucun résultat pour: {query}")
                return None
            
            # Si c'est une playlist, prendre la première vidéo
            if 'entries' in data:
                data = data['entries'][0]
            
            return self._create_track(data, requester)
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche YouTube: {e}")
            return None
    
    async def extract_playlist(self, url: str, requester: discord.Member) -> List[Track]:
        """
        Extrait toutes les vidéos d'une playlist YouTube
        
        Args:
            url: URL de la playlist YouTube
            requester: Membre Discord qui a fait la demande
            
        Returns:
            Liste de Tracks
        """
        try:
            # Options modifiées pour accepter les playlists
            ytdl_playlist = yt_dlp.YoutubeDL({
                **self.YTDL_OPTIONS,
                'noplaylist': False,
                'extract_flat': True,  # Ne pas télécharger, juste extraire les infos
            })
            
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: ytdl_playlist.extract_info(url, download=False)
            )
            
            if data is None or 'entries' not in data:
                logger.warning(f"Playlist vide ou invalide: {url}")
                return []
            
            tracks = []
            for entry in data['entries']:
                if entry:
                    # Extraire les infos complètes pour chaque vidéo
                    video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                    track = await self.search(video_url, requester)
                    if track:
                        tracks.append(track)
            
            logger.info(f"Playlist extraite: {len(tracks)} pistes")
            return tracks
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction de la playlist: {e}")
            return []
    
    def _create_track(self, data: Dict[str, Any], requester: discord.Member) -> Track:
        """
        Crée un objet Track à partir des données YouTube
        
        Args:
            data: Données extraites par yt-dlp
            requester: Membre Discord qui a fait la demande
            
        Returns:
            Track créé
        """
        # Récupérer la miniature (thumbnail)
        thumbnail = data.get('thumbnail', '')
        if not thumbnail and 'thumbnails' in data and data['thumbnails']:
            thumbnail = data['thumbnails'][-1]['url']
        
        return Track(
            title=data.get('title', 'Titre inconnu'),
            url=data.get('webpage_url', data.get('url', '')),
            stream_url=None,  # Ne pas stocker l'URL du stream, elle sera régénérée avant la lecture
            duration=data.get('duration', 0),
            thumbnail=thumbnail,
            source='youtube',
            requester=requester
        )
    
    async def get_fresh_stream_url(self, track: Track) -> Optional[str]:
        """
        Récupère une URL de stream fraîche pour une piste
        Cette méthode doit être appelée juste avant la lecture pour éviter l'expiration
        
        Args:
            track: Track pour laquelle obtenir l'URL
            
        Returns:
            URL du stream ou None si erreur
        """
        try:
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: self.ytdl.extract_info(track.url, download=False)
            )
            
            if data is None:
                logger.error(f"Impossible de régénérer l'URL pour: {track.title}")
                return None
            
            # Si c'est une playlist, prendre la première vidéo
            if 'entries' in data:
                data = data['entries'][0]
            
            stream_url = data.get('url')
            logger.info(f"URL de stream régénérée pour: {track.title}")
            return stream_url
            
        except Exception as e:
            logger.error(f"Erreur lors de la régénération de l'URL: {e}")
            return None
    
    @staticmethod
    def create_audio_source(stream_url: str):
        """
        Crée une source audio FFmpeg pour discord.py
        
        Args:
            stream_url: URL du stream audio
            
        Returns:
            discord.FFmpegPCMAudio
        """
        return discord.FFmpegPCMAudio(
            stream_url,
            **YouTubeSource.FFMPEG_OPTIONS
        )
