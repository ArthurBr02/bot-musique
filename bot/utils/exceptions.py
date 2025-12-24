"""Exceptions personnalisées pour le bot musical"""


class MusicError(Exception):
    """Exception de base pour toutes les erreurs musicales"""
    
    def __init__(self, message: str = "Une erreur musicale s'est produite"):
        self.message = message
        super().__init__(self.message)


class NotInVoiceChannel(MusicError):
    """L'utilisateur n'est pas dans un canal vocal"""
    
    def __init__(self, message: str = "Vous devez être dans un canal vocal pour utiliser cette commande"):
        super().__init__(message)


class BotNotConnected(MusicError):
    """Le bot n'est pas connecté à un canal vocal"""
    
    def __init__(self, message: str = "Le bot n'est pas connecté à un canal vocal"):
        super().__init__(message)


class TrackNotFound(MusicError):
    """Piste non trouvée"""
    
    def __init__(self, query: str = "", message: str = ""):
        if not message:
            message = f"Impossible de trouver la piste: {query}" if query else "Impossible de trouver cette piste"
        super().__init__(message)
        self.query = query


class PlaylistNotFound(MusicError):
    """Playlist non trouvée"""
    
    def __init__(self, playlist_name: str = "", message: str = ""):
        if not message:
            message = f"Playlist '{playlist_name}' introuvable" if playlist_name else "Playlist introuvable"
        super().__init__(message)
        self.playlist_name = playlist_name


class ConnectionTimeout(MusicError):
    """Timeout lors de la connexion au canal vocal"""
    
    def __init__(self, message: str = "Timeout lors de la connexion au canal vocal"):
        super().__init__(message)


class QueueEmpty(MusicError):
    """La queue est vide"""
    
    def __init__(self, message: str = "La file d'attente est vide"):
        super().__init__(message)


class InvalidVolume(MusicError):
    """Valeur de volume invalide"""
    
    def __init__(self, volume: float = 0, message: str = ""):
        if not message:
            message = f"Volume invalide: {volume}. Le volume doit être entre 0 et 100"
        super().__init__(message)
        self.volume = volume
