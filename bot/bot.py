"""Classe principale du bot Discord musical"""

import asyncio
import logging
from typing import Dict, Optional
import discord
from discord.ext import commands

from bot.config import Config
from bot.audio.player import MusicPlayer
from bot.database.sqlite import SQLiteDatabase

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
        
        # Base de données pour les playlists
        self.db: Optional[SQLiteDatabase] = None
        
    async def setup_hook(self):
        """Hook appelé lors de l'initialisation du bot"""
        logger.info("Initialisation du bot...")
        
        # Initialiser la base de données
        self.db = SQLiteDatabase()
        await self.db.init()
        
        # Charger les cogs (modules de commandes)
        await self._load_cogs()
        
    async def _load_cogs(self):
        """Charge dynamiquement tous les cogs disponibles"""
        cogs_to_load = [
            'bot.cogs.music',      # Commandes musicales
            'bot.cogs.playlist',   # Gestion des playlists
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
        # Gérer les exceptions personnalisées de musique
        if isinstance(error, commands.CommandInvokeError):
            original_error = error.original
            
            if isinstance(original_error, NotInVoiceChannel):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, BotNotConnected):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, TrackNotFound):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, PlaylistNotFound):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, ConnectionTimeout):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, QueueEmpty):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_WARNING
                    )
                )
                return
            
            elif isinstance(original_error, InvalidVolume):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
            
            elif isinstance(original_error, MusicError):
                await ctx.send(
                    embed=discord.Embed(
                        description=f"❌ {original_error.message}",
                        color=Config.COLOR_ERROR
                    )
                )
                return
        
        # Gérer les erreurs standard de discord.py
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
    
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Événement déclenché lors d'un changement d'état vocal"""
        # Vérifier si le bot est dans un canal vocal sur ce serveur
        if member.guild.id not in self.players:
            return
        
        player = self.players[member.guild.id]
        
        # Vérifier si le bot est connecté
        if not player.is_connected() or not player.voice_client:
            return
        
        # Obtenir le canal vocal du bot
        bot_channel = player.voice_client.channel
        
        # Compter le nombre de membres (hors bots) dans le canal
        members_in_channel = [m for m in bot_channel.members if not m.bot]
        
        # Si le bot est seul, démarrer un timer pour déconnexion
        if len(members_in_channel) == 0:
            logger.info(f"Bot seul dans le canal vocal - {member.guild.name}")
            # Attendre le timeout avant de déconnecter
            await asyncio.sleep(Config.ALONE_TIMEOUT)
            
            # Revérifier après le timeout
            if player.is_connected() and player.voice_client:
                bot_channel = player.voice_client.channel
                members_in_channel = [m for m in bot_channel.members if not m.bot]
                
                if len(members_in_channel) == 0:
                    logger.info(f"Déconnexion (seul dans le canal pendant {Config.ALONE_TIMEOUT}s) - {member.guild.name}")
                    await player.disconnect()
    
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
        
        # Fermer la base de données
        if self.db:
            await self.db.close()
        
        await super().close()
