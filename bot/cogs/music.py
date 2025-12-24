"""Cog de commandes musicales pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord.ext import commands

from bot.audio.player import MusicPlayer
from bot.utils.embeds import MusicEmbeds

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    """Commandes de lecture musicale"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _get_player(self, ctx: commands.Context) -> MusicPlayer:
        """Récupère le player pour le serveur actuel"""
        return self.bot.get_player(ctx.guild)
    
    async def _ensure_voice(self, ctx: commands.Context) -> bool:
        """
        Vérifie que l'utilisateur et le bot sont dans un canal vocal
        
        Returns:
            True si tout est OK, False sinon
        """
        # Vérifier que l'utilisateur est dans un canal vocal
        if not ctx.author.voice:
            await ctx.send(embed=MusicEmbeds.error(
                "Vous devez être dans un canal vocal pour utiliser cette commande."
            ))
            return False
        
        # Vérifier que le bot peut se connecter
        player = self._get_player(ctx)
        if not player.is_connected():
            # Connecter le bot au canal de l'utilisateur
            success = await player.connect(ctx.author.voice.channel)
            if not success:
                await ctx.send(embed=MusicEmbeds.error(
                    "Impossible de se connecter au canal vocal."
                ))
                return False
        
        return True
    
    @commands.command(name='play', aliases=['p'])
    async def play(self, ctx: commands.Context, *, query: str):
        """
        Joue une musique depuis YouTube ou l'ajoute à la queue
        
        Usage: !play <URL ou recherche>
        """
        # Vérifier les conditions vocales
        if not await self._ensure_voice(ctx):
            return
        
        player = self._get_player(ctx)
        
        # Message de chargement
        loading_msg = await ctx.send(embed=MusicEmbeds.info(
            f"🔍 Recherche en cours: `{query}`...",
            "Chargement"
        ))
        
        try:
            # Rechercher la piste
            track = await player.youtube_source.search(query, ctx.author)
            
            if not track:
                await loading_msg.edit(embed=MusicEmbeds.error(
                    f"Aucun résultat trouvé pour: `{query}`"
                ))
                return
            
            # Ajouter à la queue
            position = await player.add_track(track)
            
            # Si c'est la seule piste et que rien ne joue, elle va démarrer automatiquement
            if position == 1 and not player.is_playing():
                await loading_msg.edit(embed=MusicEmbeds.now_playing(track))
            else:
                await loading_msg.edit(embed=MusicEmbeds.added_to_queue(track, position))
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture: {e}")
            await loading_msg.edit(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la recherche."
            ))
    
    @commands.command(name='pause')
    async def pause(self, ctx: commands.Context):
        """
        Met en pause la lecture en cours
        
        Usage: !pause
        """
        player = self._get_player(ctx)
        
        if not player.is_connected():
            await ctx.send(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        if await player.pause():
            await ctx.send(embed=MusicEmbeds.success(
                "⏸️ Lecture mise en pause."
            ))
        else:
            await ctx.send(embed=MusicEmbeds.error(
                "Aucune musique n'est en cours de lecture."
            ))
    
    @commands.command(name='resume', aliases=['unpause'])
    async def resume(self, ctx: commands.Context):
        """
        Reprend la lecture en pause
        
        Usage: !resume
        """
        player = self._get_player(ctx)
        
        if not player.is_connected():
            await ctx.send(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        if await player.resume():
            await ctx.send(embed=MusicEmbeds.success(
                "▶️ Lecture reprise."
            ))
        else:
            await ctx.send(embed=MusicEmbeds.error(
                "La lecture n'est pas en pause."
            ))
    
    @commands.command(name='skip', aliases=['s', 'next'])
    async def skip(self, ctx: commands.Context):
        """
        Passe à la piste suivante
        
        Usage: !skip
        """
        player = self._get_player(ctx)
        
        if not player.is_connected():
            await ctx.send(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        if await player.skip():
            await ctx.send(embed=MusicEmbeds.success(
                "⏭️ Piste passée."
            ))
        else:
            await ctx.send(embed=MusicEmbeds.error(
                "Aucune musique n'est en cours de lecture."
            ))
    
    @commands.command(name='stop')
    async def stop(self, ctx: commands.Context):
        """
        Arrête la lecture et vide la queue
        
        Usage: !stop
        """
        player = self._get_player(ctx)
        
        if not player.is_connected():
            await ctx.send(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        await player.stop()
        await ctx.send(embed=MusicEmbeds.success(
            "⏹️ Lecture arrêtée et file d'attente vidée."
        ))
    
    @commands.command(name='queue', aliases=['q'])
    async def queue(self, ctx: commands.Context, page: int = 1):
        """
        Affiche la file d'attente
        
        Usage: !queue [page]
        """
        player = self._get_player(ctx)
        
        embed = await MusicEmbeds.queue_list(
            player.queue,
            player.current,
            page
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='nowplaying', aliases=['np', 'current'])
    async def nowplaying(self, ctx: commands.Context):
        """
        Affiche la piste en cours de lecture
        
        Usage: !nowplaying
        """
        player = self._get_player(ctx)
        
        if not player.current:
            await ctx.send(embed=MusicEmbeds.info(
                "Aucune musique n'est en cours de lecture."
            ))
            return
        
        await ctx.send(embed=MusicEmbeds.now_playing(player.current))
    
    @commands.command(name='volume', aliases=['vol', 'v'])
    async def volume(self, ctx: commands.Context, volume: int):
        """
        Règle le volume de lecture (0-100)
        
        Usage: !volume <0-100>
        """
        if not 0 <= volume <= 100:
            await ctx.send(embed=MusicEmbeds.error(
                "Le volume doit être entre 0 et 100."
            ))
            return
        
        player = self._get_player(ctx)
        player.set_volume(volume / 100)
        
        await ctx.send(embed=MusicEmbeds.success(
            f"🔊 Volume réglé à {volume}%."
        ))
    
    @commands.command(name='disconnect', aliases=['dc', 'leave'])
    async def disconnect(self, ctx: commands.Context):
        """
        Déconnecte le bot du canal vocal
        
        Usage: !disconnect
        """
        player = self._get_player(ctx)
        
        if not player.is_connected():
            await ctx.send(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        await player.disconnect()
        await ctx.send(embed=MusicEmbeds.success(
            "👋 Déconnecté du canal vocal."
        ))
    
    @commands.command(name='loop', aliases=['repeat'])
    async def loop(self, ctx: commands.Context):
        """
        Active/désactive la répétition de la piste actuelle
        
        Usage: !loop
        """
        player = self._get_player(ctx)
        player.loop = not player.loop
        
        status = "activée" if player.loop else "désactivée"
        emoji = "🔁" if player.loop else "➡️"
        
        await ctx.send(embed=MusicEmbeds.success(
            f"{emoji} Répétition {status}."
        ))


async def setup(bot):
    """Fonction requise pour charger le cog"""
    await bot.add_cog(Music(bot))
