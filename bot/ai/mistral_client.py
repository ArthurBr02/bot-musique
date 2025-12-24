"""Client wrapper pour l'API Mistral AI"""

import logging
from typing import List, Dict, Optional
from mistralai import Mistral

from bot.config import Config

logger = logging.getLogger(__name__)


class MistralClient:
    """Wrapper pour l'API Mistral AI"""
    
    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        max_tokens: int = None,
        temperature: float = None
    ):
        """
        Initialise le client Mistral
        
        Args:
            api_key: Clé API Mistral (par défaut depuis Config)
            model: Modèle à utiliser (par défaut depuis Config)
            max_tokens: Nombre maximum de tokens (par défaut depuis Config)
            temperature: Température pour la génération (par défaut depuis Config)
        """
        self.api_key = api_key or Config.MISTRAL_API_KEY
        self.model = model or Config.MISTRAL_MODEL
        self.max_tokens = max_tokens or Config.MISTRAL_MAX_TOKENS
        self.temperature = temperature or Config.MISTRAL_TEMPERATURE
        
        if not self.api_key:
            raise ValueError("Clé API Mistral manquante")
        
        self.client = Mistral(api_key=self.api_key)
        logger.info(f"Client Mistral initialisé avec le modèle: {self.model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Envoie une requête de chat completion à Mistral
        
        Args:
            messages: Liste des messages de conversation
            system_prompt: Prompt système optionnel
            
        Returns:
            Réponse de l'IA
            
        Raises:
            Exception: En cas d'erreur API
        """
        try:
            # Ajouter le prompt système si fourni
            if system_prompt:
                messages = [
                    {"role": "system", "content": system_prompt},
                    *messages
                ]
            
            logger.debug(f"Envoi de {len(messages)} message(s) à Mistral")
            
            # Appel à l'API Mistral
            response = self.client.chat.complete(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            # Extraire la réponse
            if response and response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logger.debug(f"Réponse reçue: {len(content)} caractères")
                return content
            else:
                logger.error("Réponse vide de l'API Mistral")
                raise ValueError("Réponse vide de l'API")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'appel à l'API Mistral: {e}")
            raise
    
    def format_conversation_history(
        self,
        messages: List
    ) -> List[Dict[str, str]]:
        """
        Formate l'historique de conversation pour l'API
        
        Args:
            messages: Liste de ConversationMessage
            
        Returns:
            Liste formatée pour l'API Mistral
        """
        return [msg.to_api_format() for msg in messages]
