"""Cog de gestion des playlists pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord.ext import commands

from bot.database.sqlite import SQLiteDatabase
from bot.database.models import Playlist
from bot.audio.player import MusicPlayer
from bot.utils.embeds import MusicEmbeds

logger = logging.getLogger(__name__)


class PlaylistCog(commands.Cog, name="Playlist"):
    """Gestion des playlists personnalisées"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: SQLiteDatabase = bot.db
    
    def _get_player(self, ctx: commands.Context) -> MusicPlayer:
        """Récupère le player pour le serveur actuel"""
        return self.bot.get_player(ctx.guild)
    
    @commands.command(name='save_playlist', aliases=['savepl'])
    async def save_playlist(self, ctx: commands.Context, *, name: str):
        """
        Sauvegarde la queue actuelle comme playlist
        
        Usage: !save_playlist <nom>
        """
        player = self._get_player(ctx)
        
        # Vérifier que la queue n'est pas vide
        queue_tracks = await player.queue.get_list()
        if not queue_tracks and not player.current:
            await ctx.send(embed=MusicEmbeds.error(
                "La file d'attente est vide. Ajoutez des pistes avant de sauvegarder."
            ))
            return
        
        try:
            # Créer la playlist
            playlist = await self.db.create_playlist(
                name=name,
                guild_id=ctx.guild.id,
                owner_id=ctx.author.id
            )
            
            # Ajouter la piste actuelle si elle existe
            if player.current:
                await self.db.add_track_to_playlist(playlist.id, player.current)
            
            # Ajouter toutes les pistes de la queue
            for track in queue_tracks:
                await self.db.add_track_to_playlist(playlist.id, track)
            
            # Récupérer la playlist mise à jour
            playlist = await self.db.get_playlist(playlist.id)
            
            embed = discord.Embed(
                title="✅ Playlist sauvegardée",
                description=f"**{name}**",
                color=MusicEmbeds.success("").color
            )
            embed.add_field(name="Pistes", value=str(playlist.track_count), inline=True)
            embed.add_field(name="Durée", value=playlist.duration_formatted, inline=True)
            
            await ctx.send(embed=embed)
            logger.info(f"Playlist sauvegardée: {name} ({playlist.track_count} pistes)")
            
        except ValueError as e:
            await ctx.send(embed=MusicEmbeds.error(str(e)))
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la playlist: {e}")
            await ctx.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la sauvegarde de la playlist."
            ))
    
    @commands.command(name='load_playlist', aliases=['loadpl'])
    async def load_playlist(self, ctx: commands.Context, *, name: str):
        """
        Charge une playlist dans la queue
        
        Usage: !load_playlist <nom>
        """
        # Vérifier que l'utilisateur est dans un canal vocal
        if not ctx.author.voice:
            await ctx.send(embed=MusicEmbeds.error(
                "Vous devez être dans un canal vocal pour charger une playlist."
            ))
            return
        
        try:
            # Récupérer la playlist
            playlist = await self.db.get_playlist_by_name(name, ctx.guild.id)
            
            if not playlist:
                await ctx.send(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            if not playlist.tracks:
                await ctx.send(embed=MusicEmbeds.warning(
                    f"La playlist '{name}' est vide."
                ))
                return
            
            player = self._get_player(ctx)
            
            # Connecter le bot si nécessaire
            if not player.is_connected():
                await player.connect(ctx.author.voice.channel)
            
            # Message de chargement
            loading_msg = await ctx.send(embed=MusicEmbeds.info(
                f"⏳ Chargement de la playlist **{name}**...",
                "Chargement"
            ))
            
            # Ajouter toutes les pistes à la queue
            added_count = 0
            for pl_track in playlist.tracks:
                # Rechercher la piste pour obtenir les métadonnées complètes
                track = await player.youtube_source.search(pl_track.url, ctx.author)
                if track:
                    await player.add_track(track)
                    added_count += 1
            
            embed = discord.Embed(
                title="✅ Playlist chargée",
                description=f"**{name}**",
                color=MusicEmbeds.success("").color
            )
            embed.add_field(name="Pistes ajoutées", value=str(added_count), inline=True)
            embed.add_field(name="Durée", value=playlist.duration_formatted, inline=True)
            
            await loading_msg.edit(embed=embed)
            logger.info(f"Playlist chargée: {name} ({added_count} pistes)")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la playlist: {e}")
            await ctx.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors du chargement de la playlist."
            ))
    
    @commands.command(name='list_playlists', aliases=['playlists', 'pls'])
    async def list_playlists(self, ctx: commands.Context):
        """
        Liste toutes les playlists du serveur
        
        Usage: !list_playlists
        """
        try:
            playlists = await self.db.get_playlists_by_guild(ctx.guild.id)
            
            if not playlists:
                await ctx.send(embed=MusicEmbeds.info(
                    "Aucune playlist sauvegardée sur ce serveur."
                ))
                return
            
            # Créer l'embed
            embed = discord.Embed(
                title=f"📋 Playlists de {ctx.guild.name}",
                color=MusicEmbeds.info("").color
            )
            
            for playlist in playlists[:25]:  # Limiter à 25 pour ne pas dépasser la limite Discord
                owner = ctx.guild.get_member(playlist.owner_id)
                owner_name = owner.display_name if owner else "Inconnu"
                
                value = f"👤 {owner_name} • {playlist.track_count} piste(s) • {playlist.duration_formatted}"
                embed.add_field(
                    name=playlist.name,
                    value=value,
                    inline=False
                )
            
            if len(playlists) > 25:
                embed.set_footer(text=f"... et {len(playlists) - 25} autres playlists")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des playlists: {e}")
            await ctx.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la récupération des playlists."
            ))
    
    @commands.command(name='remove_playlist', aliases=['deletepl', 'delpl'])
    async def remove_playlist(self, ctx: commands.Context, *, name: str):
        """
        Supprime une playlist
        
        Usage: !remove_playlist <nom>
        """
        try:
            # Récupérer la playlist
            playlist = await self.db.get_playlist_by_name(name, ctx.guild.id)
            
            if not playlist:
                await ctx.send(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            # Vérifier que l'utilisateur est le propriétaire ou a les permissions
            if playlist.owner_id != ctx.author.id and not ctx.author.guild_permissions.manage_guild:
                await ctx.send(embed=MusicEmbeds.error(
                    "Vous n'avez pas la permission de supprimer cette playlist."
                ))
                return
            
            # Supprimer la playlist
            await self.db.delete_playlist(playlist.id)
            
            await ctx.send(embed=MusicEmbeds.success(
                f"🗑️ Playlist **{name}** supprimée."
            ))
            logger.info(f"Playlist supprimée: {name}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la playlist: {e}")
            await ctx.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la suppression de la playlist."
            ))
    
    @commands.command(name='playlist_info', aliases=['plinfo'])
    async def playlist_info(self, ctx: commands.Context, *, name: str):
        """
        Affiche les détails d'une playlist
        
        Usage: !playlist_info <nom>
        """
        try:
            playlist = await self.db.get_playlist_by_name(name, ctx.guild.id)
            
            if not playlist:
                await ctx.send(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            owner = ctx.guild.get_member(playlist.owner_id)
            owner_name = owner.mention if owner else "Inconnu"
            
            embed = discord.Embed(
                title=f"📋 {playlist.name}",
                color=MusicEmbeds.info("").color
            )
            
            embed.add_field(name="Propriétaire", value=owner_name, inline=True)
            embed.add_field(name="Pistes", value=str(playlist.track_count), inline=True)
            embed.add_field(name="Durée", value=playlist.duration_formatted, inline=True)
            
            # Afficher les 10 premières pistes
            if playlist.tracks:
                tracks_text = ""
                for i, track in enumerate(playlist.tracks[:10], 1):
                    minutes, seconds = divmod(track.duration, 60)
                    tracks_text += f"`{i}.` {track.title} - `{minutes}:{seconds:02d}`\n"
                
                if len(playlist.tracks) > 10:
                    tracks_text += f"\n... et {len(playlist.tracks) - 10} autres pistes"
                
                embed.add_field(name="Pistes", value=tracks_text, inline=False)
            
            embed.set_footer(text=f"Créée le {playlist.created_at.strftime('%d/%m/%Y à %H:%M')}")
            
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage de la playlist: {e}")
            await ctx.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de l'affichage de la playlist."
            ))


async def setup(bot):
    """Fonction requise pour charger le cog"""
    await bot.add_cog(PlaylistCog(bot))
