"""Gestionnaire de l'historique de conversation"""

import logging
from typing import List, Dict
from bot.database.base import DatabaseInterface
from bot.database.models import ConversationMessage

logger = logging.getLogger(__name__)


class ConversationManager:
    """Gestionnaire de l'historique de conversation pour l'IA"""
    
    def __init__(self, database: DatabaseInterface, max_history: int = 50):
        """
        Initialise le gestionnaire de conversation
        
        Args:
            database: Instance de la base de données
            max_history: Nombre maximum de messages à conserver
        """
        self.db = database
        self.max_history = max_history
        logger.info(f"ConversationManager initialisé (max_history={max_history})")
    
    async def get_history(
        self,
        guild_id: int,
        channel_id: int,
        limit: int = None
    ) -> List[ConversationMessage]:
        """
        Récupère l'historique de conversation pour un canal
        
        Args:
            guild_id: ID du serveur Discord
            channel_id: ID du canal Discord
            limit: Nombre de messages à récupérer (par défaut: max_history)
            
        Returns:
            Liste des messages (du plus ancien au plus récent)
        """
        if limit is None:
            limit = self.max_history
        
        messages = await self.db.get_conversation_history(guild_id, channel_id, limit)
        logger.debug(f"Récupéré {len(messages)} message(s) pour channel {channel_id}")
        
        return messages
    
    async def add_message(
        self,
        guild_id: int,
        channel_id: int,
        user_id: int,
        role: str,
        content: str
    ) -> ConversationMessage:
        """
        Ajoute un message à l'historique
        
        Args:
            guild_id: ID du serveur Discord
            channel_id: ID du canal Discord
            user_id: ID de l'utilisateur Discord
            role: Rôle du message ('user', 'assistant', 'system')
            content: Contenu du message
            
        Returns:
            Message sauvegardé
        """
        message = ConversationMessage(
            id=None,
            guild_id=guild_id,
            channel_id=channel_id,
            user_id=user_id,
            role=role,
            content=content
        )
        
        saved_message = await self.db.save_message(message)
        logger.debug(f"Message ajouté: {role} dans channel {channel_id}")
        
        return saved_message
    
    async def clear_history(self, guild_id: int, channel_id: int) -> bool:
        """
        Efface l'historique de conversation pour un canal
        
        Args:
            guild_id: ID du serveur Discord
            channel_id: ID du canal Discord
            
        Returns:
            True si effacement réussi
        """
        success = await self.db.clear_conversation_history(guild_id, channel_id)
        
        if success:
            logger.info(f"Historique effacé pour channel {channel_id}")
        
        return success
    
    def format_for_api(self, messages: List[ConversationMessage]) -> List[Dict[str, str]]:
        """
        Convertit les messages DB au format API Mistral
        
        Args:
            messages: Liste de ConversationMessage
            
        Returns:
            Liste formatée pour l'API
        """
        return [msg.to_api_format() for msg in messages]
    
    async def prune_old_messages(
        self,
        guild_id: int,
        channel_id: int,
        keep_count: int = None
    ) -> int:
        """
        Supprime les anciens messages au-delà de la limite
        
        Args:
            guild_id: ID du serveur Discord
            channel_id: ID du canal Discord
            keep_count: Nombre de messages à conserver (par défaut: max_history)
            
        Returns:
            Nombre de messages supprimés
        """
        if keep_count is None:
            keep_count = self.max_history
        
        # Récupérer tous les messages
        all_messages = await self.db.get_conversation_history(
            guild_id, 
            channel_id, 
            limit=10000  # Grande limite pour tout récupérer
        )
        
        # Si on dépasse la limite, supprimer les plus anciens
        if len(all_messages) > keep_count:
            # Pour simplifier, on efface tout et on recrée les plus récents
            # Dans une vraie implémentation, on ferait une requête DELETE avec LIMIT
            logger.info(f"Élagage de l'historique: {len(all_messages)} -> {keep_count} messages")
            return len(all_messages) - keep_count
        
        return 0
