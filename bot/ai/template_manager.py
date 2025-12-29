"""Gestionnaire de templates IA"""

import logging
from typing import Optional, List
from bot.database.base import DatabaseInterface
from bot.database.models import AITemplate

logger = logging.getLogger(__name__)


class TemplateManager:
    """Gestionnaire de templates de prompts IA"""
    
    # Template par défaut si aucun n'est configuré
    DEFAULT_TEMPLATE = """Tu es un assistant IA utile et amical dans un serveur Discord. 
Tu réponds de manière concise et claire aux questions des utilisateurs.
Adapte ton ton à la conversation et reste respectueux."""

    RULES = """Les messages des utilisateurs sont préfixés par leur pseudo Discord au format "Pseudo: message".
Fais attention à qui parle et utilise les pseudos pour t'adresser aux utilisateurs de manière personnalisée.
Dans les conversations multi-utilisateurs, distingue clairement les différents interlocuteurs."""
    
    def __init__(self, database: DatabaseInterface):
        """
        Initialise le gestionnaire de templates
        
        Args:
            database: Instance de la base de données
        """
        self.db = database
        logger.info("TemplateManager initialisé")
    
    async def get_active_template(self, guild_id: int) -> str:
        """
        Récupère le prompt système actif pour un serveur
        
        Args:
            guild_id: ID du serveur Discord
            
        Returns:
            Prompt système (template actif ou défaut)
        """
        template = await self.db.get_active_template(guild_id)
        
        if template:
            logger.debug(f"Template actif trouvé pour guild {guild_id}: {template.name}")
            return template.system_prompt + "\n\n" + self.RULES
        else:
            logger.debug(f"Aucun template actif pour guild {guild_id}, utilisation du défaut")
            return self.DEFAULT_TEMPLATE + "\n\n" + self.RULES
    
    async def create_template(
        self,
        guild_id: int,
        name: str,
        system_prompt: str,
        set_active: bool = False
    ) -> AITemplate:
        """
        Crée un nouveau template
        
        Args:
            guild_id: ID du serveur Discord
            name: Nom du template
            system_prompt: Contenu du prompt système
            set_active: Si True, active immédiatement ce template
            
        Returns:
            Template créé
            
        Raises:
            ValueError: Si un template avec ce nom existe déjà
        """
        template = AITemplate(
            id=None,
            guild_id=guild_id,
            name=name,
            system_prompt=system_prompt,
            is_active=False
        )
        
        saved_template = await self.db.save_template(template)
        logger.info(f"Template créé: {name} pour guild {guild_id}")
        
        if set_active:
            await self.set_active(guild_id, saved_template.id)
        
        return saved_template
    
    async def update_template(
        self,
        template_id: int,
        system_prompt: str
    ) -> AITemplate:
        """
        Met à jour le contenu d'un template
        
        Args:
            template_id: ID du template
            system_prompt: Nouveau contenu du prompt
            
        Returns:
            Template mis à jour
        """
        # Récupérer le template existant
        templates = await self.db.get_all_templates(0)  # On va le chercher différemment
        template = None
        
        for t in templates:
            if t.id == template_id:
                template = t
                break
        
        if not template:
            raise ValueError(f"Template {template_id} non trouvé")
        
        template.system_prompt = system_prompt
        updated = await self.db.save_template(template)
        
        logger.info(f"Template {template_id} mis à jour")
        return updated
    
    async def delete_template(self, template_id: int) -> bool:
        """
        Supprime un template
        
        Args:
            template_id: ID du template à supprimer
            
        Returns:
            True si suppression réussie
        """
        success = await self.db.delete_template(template_id)
        
        if success:
            logger.info(f"Template {template_id} supprimé")
        
        return success
    
    async def set_active(self, guild_id: int, template_id: int) -> bool:
        """
        Définit le template actif pour un serveur
        
        Args:
            guild_id: ID du serveur
            template_id: ID du template à activer
            
        Returns:
            True si activation réussie
        """
        success = await self.db.set_active_template(guild_id, template_id)
        
        if success:
            logger.info(f"Template {template_id} activé pour guild {guild_id}")
        
        return success
    
    async def list_templates(self, guild_id: int) -> List[AITemplate]:
        """
        Liste tous les templates d'un serveur
        
        Args:
            guild_id: ID du serveur
            
        Returns:
            Liste des templates
        """
        templates = await self.db.get_all_templates(guild_id)
        logger.debug(f"{len(templates)} template(s) trouvé(s) pour guild {guild_id}")
        return templates
    
    def get_default_template(self) -> str:
        """
        Retourne le template par défaut
        
        Returns:
            Prompt système par défaut
        """
        return self.DEFAULT_TEMPLATE
