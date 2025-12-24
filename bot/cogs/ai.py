"""Cog de commandes IA pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from bot.config import Config
from bot.ai.mistral_client import MistralClient
from bot.ai.template_manager import TemplateManager
from bot.ai.conversation_manager import ConversationManager

logger = logging.getLogger(__name__)


class AI(commands.Cog):
    """Commandes de chatbot IA avec Mistral"""
    
    def __init__(self, bot):
        self.bot = bot
        self.mistral_client: Optional[MistralClient] = None
        self.template_manager: Optional[TemplateManager] = None
        self.conversation_manager: Optional[ConversationManager] = None
        
        # Initialiser les composants IA si Mistral est configuré
        if Config.has_mistral():
            try:
                self.mistral_client = MistralClient()
                self.template_manager = TemplateManager(bot.db)
                self.conversation_manager = ConversationManager(bot.db, max_history=50)
                logger.info("Composants IA initialisés avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation des composants IA: {e}")
        else:
            logger.warning("Mistral non configuré - Commandes IA désactivées")
    
    def _check_ai_available(self) -> bool:
        """Vérifie si l'IA est disponible"""
        return self.mistral_client is not None
    
    @app_commands.command(name="chat", description="Discute avec l'IA")
    @app_commands.describe(message="Ton message pour l'IA")
    async def chat(self, interaction: discord.Interaction, message: str):
        """Envoie un message au chatbot IA"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            guild_id = interaction.guild_id
            channel_id = interaction.channel_id
            user_id = interaction.user.id
            
            # Récupérer le template actif
            system_prompt = await self.template_manager.get_active_template(guild_id)
            
            # Récupérer l'historique de conversation
            history = await self.conversation_manager.get_history(guild_id, channel_id, limit=20)
            
            # Ajouter le message de l'utilisateur à l'historique
            await self.conversation_manager.add_message(
                guild_id, channel_id, user_id, "user", message
            )
            
            # Formater l'historique pour l'API
            api_messages = self.conversation_manager.format_for_api(history)
            
            # Ajouter le nouveau message
            api_messages.append({"role": "user", "content": message})
            
            # Obtenir la réponse de l'IA
            response = await self.mistral_client.chat_completion(api_messages, system_prompt)
            
            # Sauvegarder la réponse dans l'historique
            await self.conversation_manager.add_message(
                guild_id, channel_id, self.bot.user.id, "assistant", response
            )
            
            # Envoyer la réponse
            # Si la réponse est trop longue, la diviser
            if len(response) > 2000:
                # Envoyer en plusieurs messages
                chunks = [response[i:i+2000] for i in range(0, len(response), 2000)]
                await interaction.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await interaction.channel.send(chunk)
            else:
                await interaction.followup.send(response)
            
        except Exception as e:
            logger.error(f"Erreur lors du chat IA: {e}")
            await interaction.followup.send(
                embed=discord.Embed(
                    description=f"❌ Erreur lors de la communication avec l'IA: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
    
    # Groupe de commandes pour les templates
    template_group = app_commands.Group(
        name="ai_template",
        description="Gestion des templates IA"
    )
    
    @template_group.command(name="list", description="Liste tous les templates IA du serveur")
    async def template_list(self, interaction: discord.Interaction):
        """Liste tous les templates IA"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        try:
            templates = await self.template_manager.list_templates(interaction.guild_id)
            
            if not templates:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description="📝 Aucun template configuré. Utilisation du template par défaut.",
                        color=Config.COLOR_INFO
                    )
                )
                return
            
            # Créer l'embed avec la liste des templates
            embed = discord.Embed(
                title="📝 Templates IA",
                description=f"{len(templates)} template(s) configuré(s)",
                color=Config.COLOR_PRIMARY
            )
            
            for template in templates:
                status = "✅ Actif" if template.is_active else "⚪ Inactif"
                preview = template.system_prompt[:100] + "..." if len(template.system_prompt) > 100 else template.system_prompt
                embed.add_field(
                    name=f"{status} - {template.name}",
                    value=f"```{preview}```",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des templates: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erreur: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
    
    @template_group.command(name="create", description="Crée un nouveau template IA")
    @app_commands.describe(
        name="Nom du template",
        system_prompt="Prompt système pour l'IA",
        set_active="Activer immédiatement ce template"
    )
    @app_commands.default_permissions(manage_guild=True)
    async def template_create(
        self,
        interaction: discord.Interaction,
        name: str,
        system_prompt: str,
        set_active: bool = False
    ):
        """Crée un nouveau template IA"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        try:
            template = await self.template_manager.create_template(
                interaction.guild_id,
                name,
                system_prompt,
                set_active=set_active
            )
            
            status_msg = " et activé" if set_active else ""
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Template **{name}** créé{status_msg} avec succès!",
                    color=Config.COLOR_SUCCESS
                )
            )
            
        except ValueError as e:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Erreur lors de la création du template: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erreur: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
    
    @template_group.command(name="set", description="Active un template IA")
    @app_commands.describe(name="Nom du template à activer")
    @app_commands.default_permissions(manage_guild=True)
    async def template_set(self, interaction: discord.Interaction, name: str):
        """Active un template IA"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        try:
            # Trouver le template par nom
            templates = await self.template_manager.list_templates(interaction.guild_id)
            template = next((t for t in templates if t.name == name), None)
            
            if not template:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"❌ Template **{name}** non trouvé.",
                        color=Config.COLOR_ERROR
                    ),
                    ephemeral=True
                )
                return
            
            # Activer le template
            await self.template_manager.set_active(interaction.guild_id, template.id)
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Template **{name}** activé!",
                    color=Config.COLOR_SUCCESS
                )
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'activation du template: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erreur: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
    
    @template_group.command(name="delete", description="Supprime un template IA")
    @app_commands.describe(name="Nom du template à supprimer")
    @app_commands.default_permissions(manage_guild=True)
    async def template_delete(self, interaction: discord.Interaction, name: str):
        """Supprime un template IA"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        try:
            # Trouver le template par nom
            templates = await self.template_manager.list_templates(interaction.guild_id)
            template = next((t for t in templates if t.name == name), None)
            
            if not template:
                await interaction.response.send_message(
                    embed=discord.Embed(
                        description=f"❌ Template **{name}** non trouvé.",
                        color=Config.COLOR_ERROR
                    ),
                    ephemeral=True
                )
                return
            
            # Supprimer le template
            await self.template_manager.delete_template(template.id)
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"✅ Template **{name}** supprimé!",
                    color=Config.COLOR_SUCCESS
                )
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du template: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erreur: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
    
    @app_commands.command(name="ai_clear", description="Efface l'historique de conversation IA")
    async def ai_clear(self, interaction: discord.Interaction):
        """Efface l'historique de conversation"""
        if not self._check_ai_available():
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ L'IA n'est pas configurée sur ce bot.",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )
            return
        
        try:
            await self.conversation_manager.clear_history(
                interaction.guild_id,
                interaction.channel_id
            )
            
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="✅ Historique de conversation effacé!",
                    color=Config.COLOR_SUCCESS
                )
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement de l'historique: {e}")
            await interaction.response.send_message(
                embed=discord.Embed(
                    description=f"❌ Erreur: {str(e)}",
                    color=Config.COLOR_ERROR
                ),
                ephemeral=True
            )


async def setup(bot):
    """Fonction requise pour charger le cog"""
    await bot.add_cog(AI(bot))
