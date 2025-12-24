"""Classe principale du bot Discord musical"""

import logging
from typing import Dict, Optional
import discord
from discord.ext import commands

from bot.config import Config
from bot.audio.player import MusicPlayer

logger = logging.getLogger(__name__)


class MusicBot(commands.Bot):
    """Bot Discord musical avec support multi-serveur"""
    
    def __init__(self):
        # Configuration des intents Discord
        intents = discord.Intents.default()
        intents.message_content = True  # Requis pour lire le contenu des messages
        intents.voice_states = True     # Requis pour la gestion audio
        intents.guilds = True           # Requis pour accéder aux serveurs
        
        super().__init__(
            command_prefix=Config.COMMAND_PREFIX,
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )
        
        # Stockage des players par guild (serveur)
        # guild_id -> MusicPlayer
        self.players: Dict[int, any] = {}
        
    async def setup_hook(self):
        """Hook appelé lors de l'initialisation du bot"""
        logger.info("Initialisation du bot...")
        
        # Charger les cogs (modules de commandes)
        await self._load_cogs()
        
    async def _load_cogs(self):
        """Charge dynamiquement tous les cogs disponibles"""
        cogs_to_load = [
            'bot.cogs.music',      # Commandes musicales
            # 'bot.cogs.playlist',   # À implémenter en Phase 4
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog chargé: {cog}")
            except Exception as e:
                logger.error(f"Erreur lors du chargement du cog {cog}: {e}")
    
    async def on_ready(self):
        """Événement déclenché quand le bot est prêt"""
        logger.info(f"Bot connecté en tant que {self.user} (ID: {self.user.id})")
        logger.info(f"Connecté à {len(self.guilds)} serveur(s)")
        
        # Définir le statut du bot
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{Config.COMMAND_PREFIX}play"
            )
        )
        
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        """Gestionnaire d'erreurs global pour les commandes"""
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(f"❌ Commande inconnue. Utilisez `{Config.COMMAND_PREFIX}help` pour voir les commandes disponibles.")
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Argument manquant: `{error.param.name}`")
        
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Argument invalide: {error}")
        
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ Vous n'avez pas les permissions nécessaires pour cette commande.")
        
        else:
            logger.error(f"Erreur non gérée dans la commande {ctx.command}: {error}", exc_info=error)
            await ctx.send("❌ Une erreur inattendue s'est produite.")
    
    async def on_guild_join(self, guild: discord.Guild):
        """Événement déclenché quand le bot rejoint un serveur"""
        logger.info(f"Bot ajouté au serveur: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild: discord.Guild):
        """Événement déclenché quand le bot quitte un serveur"""
        logger.info(f"Bot retiré du serveur: {guild.name} (ID: {guild.id})")
        
        # Nettoyer le player associé si existant
        if guild.id in self.players:
            await self.players[guild.id].disconnect()
            del self.players[guild.id]
    
    def get_player(self, guild: discord.Guild) -> MusicPlayer:
        """Récupère ou crée un player pour un serveur"""
        if guild.id not in self.players:
            self.players[guild.id] = MusicPlayer(self, guild)
            logger.info(f"Player créé pour le serveur: {guild.name}")
        
        return self.players[guild.id]
    
    async def close(self):
        """Fermeture propre du bot"""
        logger.info("Fermeture du bot...")
        
        # Déconnecter tous les players
        for player in self.players.values():
            await player.disconnect()
        
        await super().close()
