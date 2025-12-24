"""Module IA pour l'intégration Mistral AI"""

from bot.ai.mistral_client import MistralClient
from bot.ai.template_manager import TemplateManager
from bot.ai.conversation_manager import ConversationManager

__all__ = ['MistralClient', 'TemplateManager', 'ConversationManager']
