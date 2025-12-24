"""Intégration Spotify avec conversion vers YouTube"""

import logging
import re
from typing import Optional, List, Tuple
from dataclasses import dataclass
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from bot.config import Config

logger = logging.getLogger(__name__)


@dataclass
class SpotifyTrackInfo:
    """Informations d'une piste Spotify"""
    
    title: str          # Titre de la piste
    artist: str         # Artiste principal
    album: str          # Album
    duration_ms: int    # Durée en millisecondes
    url: str            # URL Spotify
    
    @property
    def search_query(self) -> str:
        """Génère une query de recherche YouTube optimisée"""
        return f"{self.artist} - {self.title}"
    
    @property
    def duration_seconds(self) -> int:
        """Retourne la durée en secondes"""
        return self.duration_ms // 1000


class SpotifySource:
    """Gestionnaire d'extraction de métadonnées Spotify"""
    
    # Patterns pour extraire les IDs depuis les URLs Spotify
    TRACK_PATTERN = re.compile(r'track/([a-zA-Z0-9]+)')
    PLAYLIST_PATTERN = re.compile(r'playlist/([a-zA-Z0-9]+)')
    ALBUM_PATTERN = re.compile(r'album/([a-zA-Z0-9]+)')
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialise le client Spotify
        
        Args:
            client_id: ID client Spotify (optionnel, utilise Config par défaut)
            client_secret: Secret client Spotify (optionnel, utilise Config par défaut)
        """
        self.client_id = client_id or Config.SPOTIFY_CLIENT_ID
        self.client_secret = client_secret or Config.SPOTIFY_CLIENT_SECRET
        
        if not self.client_id or not self.client_secret:
            logger.warning("Credentials Spotify non configurés. L'intégration Spotify est désactivée.")
            self.sp = None
            return
        
        try:
            auth_manager = SpotifyClientCredentials(
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            self.sp = spotipy.Spotify(auth_manager=auth_manager)
            logger.info("Client Spotify initialisé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Spotify: {e}")
            self.sp = None
    
    def is_available(self) -> bool:
        """Vérifie si le client Spotify est disponible"""
        return self.sp is not None
    
    def extract_id_from_url(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Extrait le type et l'ID depuis une URL Spotify
        
        Args:
            url: URL Spotify
            
        Returns:
            Tuple (type, id) ou None si invalide
            type peut être: 'track', 'playlist', 'album'
        """
        # Vérifier track
        match = self.TRACK_PATTERN.search(url)
        if match:
            return ('track', match.group(1))
        
        # Vérifier playlist
        match = self.PLAYLIST_PATTERN.search(url)
        if match:
            return ('playlist', match.group(1))
        
        # Vérifier album
        match = self.ALBUM_PATTERN.search(url)
        if match:
            return ('album', match.group(1))
        
        return None
    
    def is_spotify_url(self, url: str) -> bool:
        """Vérifie si une URL est une URL Spotify"""
        return 'spotify.com' in url or 'open.spotify' in url
    
    async def get_track(self, url: str) -> Optional[SpotifyTrackInfo]:
        """
        Récupère les informations d'une piste Spotify
        
        Args:
            url: URL de la piste Spotify
            
        Returns:
            SpotifyTrackInfo ou None si erreur
        """
        if not self.is_available():
            logger.error("Client Spotify non disponible")
            return None
        
        try:
            result = self.extract_id_from_url(url)
            if not result or result[0] != 'track':
                logger.error(f"URL Spotify invalide ou non supportée: {url}")
                return None
            
            track_id = result[1]
            track = self.sp.track(track_id)
            
            return SpotifyTrackInfo(
                title=track['name'],
                artist=track['artists'][0]['name'],
                album=track['album']['name'],
                duration_ms=track['duration_ms'],
                url=track['external_urls']['spotify']
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la piste Spotify: {e}")
            return None
    
    async def get_playlist(self, url: str) -> List[SpotifyTrackInfo]:
        """
        Récupère toutes les pistes d'une playlist Spotify
        
        Args:
            url: URL de la playlist Spotify
            
        Returns:
            Liste de SpotifyTrackInfo
        """
        if not self.is_available():
            logger.error("Client Spotify non disponible")
            return []
        
        try:
            result = self.extract_id_from_url(url)
            if not result or result[0] != 'playlist':
                logger.error(f"URL de playlist Spotify invalide: {url}")
                return []
            
            playlist_id = result[1]
            tracks = []
            
            # Récupérer toutes les pistes (pagination)
            results = self.sp.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    if item and item.get('track'):
                        track = item['track']
                        # Vérifier que toutes les données nécessaires sont présentes
                        if not track.get('name') or not track.get('artists') or not track.get('album'):
                            continue
                        
                        tracks.append(SpotifyTrackInfo(
                            title=track['name'],
                            artist=track['artists'][0]['name'],
                            album=track['album']['name'],
                            duration_ms=track.get('duration_ms', 0),
                            url=track.get('external_urls', {}).get('spotify', '')
                        ))
                
                # Pagination
                if results['next']:
                    results = self.sp.next(results)
                else:
                    break
            
            logger.info(f"Playlist Spotify extraite: {len(tracks)} pistes")
            return tracks
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la playlist Spotify: {e}")
            return []
    
    async def get_album(self, url: str) -> List[SpotifyTrackInfo]:
        """
        Récupère toutes les pistes d'un album Spotify
        
        Args:
            url: URL de l'album Spotify
            
        Returns:
            Liste de SpotifyTrackInfo
        """
        if not self.is_available():
            logger.error("Client Spotify non disponible")
            return []
        
        try:
            result = self.extract_id_from_url(url)
            if not result or result[0] != 'album':
                logger.error(f"URL d'album Spotify invalide: {url}")
                return []
            
            album_id = result[1]
            album = self.sp.album(album_id)
            tracks = []
            
            for track in album['tracks']['items']:
                # Vérifier que toutes les données nécessaires sont présentes
                if not track.get('name') or not track.get('artists'):
                    continue
                
                tracks.append(SpotifyTrackInfo(
                    title=track['name'],
                    artist=track['artists'][0]['name'],
                    album=album['name'],
                    duration_ms=track.get('duration_ms', 0),
                    url=track.get('external_urls', {}).get('spotify', '')
                ))
            
            logger.info(f"Album Spotify extrait: {len(tracks)} pistes")
            return tracks
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'album Spotify: {e}")
            return []
