"""File d'attente thread-safe pour la gestion des pistes audio"""

import asyncio
from typing import List, Optional
from collections import deque
import random

from .track import Track


class MusicQueue:
    """File d'attente thread-safe pour un serveur Discord"""
    
    def __init__(self):
        self._queue: deque[Track] = deque()
        self._current: Optional[Track] = None
        self._lock = asyncio.Lock()
    
    async def add(self, track: Track) -> int:
        """
        Ajoute une piste à la queue
        
        Args:
            track: La piste à ajouter
            
        Returns:
            La position de la piste dans la queue (1-indexed)
        """
        async with self._lock:
            self._queue.append(track)
            return len(self._queue)
    
    async def next(self) -> Optional[Track]:
        """
        Récupère et retire la prochaine piste de la queue
        
        Returns:
            La prochaine piste ou None si la queue est vide
        """
        async with self._lock:
            if self._queue:
                self._current = self._queue.popleft()
                return self._current
            return None
    
    async def clear(self) -> None:
        """Vide complètement la queue"""
        async with self._lock:
            self._queue.clear()
            self._current = None
    
    async def shuffle(self) -> None:
        """Mélange aléatoirement les pistes dans la queue"""
        async with self._lock:
            queue_list = list(self._queue)
            random.shuffle(queue_list)
            self._queue = deque(queue_list)
    
    async def get_list(self) -> List[Track]:
        """
        Retourne une copie de la liste des pistes
        
        Returns:
            Liste des pistes dans la queue
        """
        async with self._lock:
            return list(self._queue)
    
    async def is_empty(self) -> bool:
        """
        Vérifie si la queue est vide
        
        Returns:
            True si la queue est vide, False sinon
        """
        async with self._lock:
            return len(self._queue) == 0
    
    async def size(self) -> int:
        """
        Retourne le nombre de pistes dans la queue
        
        Returns:
            Nombre de pistes
        """
        async with self._lock:
            return len(self._queue)
    
    def current(self) -> Optional[Track]:
        """
        Retourne la piste actuellement en cours de lecture
        
        Returns:
            La piste actuelle ou None
        """
        return self._current
    
    async def remove(self, position: int) -> Optional[Track]:
        """
        Retire une piste à une position donnée (1-indexed)
        
        Args:
            position: Position de la piste à retirer (commence à 1)
            
        Returns:
            La piste retirée ou None si position invalide
        """
        async with self._lock:
            if 1 <= position <= len(self._queue):
                # Convertir en index 0-based
                index = position - 1
                queue_list = list(self._queue)
                removed = queue_list.pop(index)
                self._queue = deque(queue_list)
                return removed
            return None
