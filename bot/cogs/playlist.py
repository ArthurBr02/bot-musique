"""Cog de gestion des playlists pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from bot.database.sqlite import SQLiteDatabase
from bot.database.models import Playlist
from bot.audio.player import MusicPlayer
from bot.utils.embeds import MusicEmbeds

logger = logging.getLogger(__name__)


class PlaylistCog(commands.Cog):
    """Gestion des playlists personnalisées"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db: SQLiteDatabase = bot.db
    
    def _get_player(self, interaction: discord.Interaction) -> MusicPlayer:
        """Récupère le player pour le serveur actuel"""
        return self.bot.get_player(interaction.guild)
    
    @app_commands.command(name="save_playlist", description="Sauvegarde la queue actuelle")
    @app_commands.describe(name="Nom de la playlist")
    async def save_playlist(self, interaction: discord.Interaction, *, name: str):
        """
        Sauvegarde la queue actuelle comme playlist
        
        Usage: !save_playlist <nom>
        """
        player = self._get_player(interaction)
        
        # Vérifier que la queue n'est pas vide
        queue_tracks = await player.queue.get_list()
        if not queue_tracks and not player.current:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "La file d'attente est vide. Ajoutez des pistes avant de sauvegarder."
            ))
            return
        
        try:
            # Créer la playlist
            playlist = await self.db.create_playlist(
                name=name,
                guild_id=interaction.guild.id,
                owner_id=interaction.user.id
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
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Playlist sauvegardée: {name} ({playlist.track_count} pistes)")
            
        except ValueError as e:
            await interaction.response.send_message(embed=MusicEmbeds.error(str(e)))
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la playlist: {e}")
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la sauvegarde de la playlist."
            ))
    
    @app_commands.command(name="load_playlist", description="Charge une playlist")
    @app_commands.describe(name="Nom de la playlist")
    async def load_playlist(self, interaction: discord.Interaction, *, name: str):
        """
        Charge une playlist dans la queue
        
        Usage: !load_playlist <nom>
        """
        # Vérifier que l'utilisateur est dans un canal vocal
        if not interaction.user.voice:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Vous devez être dans un canal vocal pour charger une playlist."
            ))
            return
        
        try:
            # Récupérer la playlist
            playlist = await self.db.get_playlist_by_name(name, interaction.guild.id)
            
            if not playlist:
                await interaction.response.send_message(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            if not playlist.tracks:
                await interaction.response.send_message(embed=MusicEmbeds.warning(
                    f"La playlist '{name}' est vide."
                ))
                return
            
            player = self._get_player(interaction)
            
            # Connecter le bot si nécessaire
            if not player.is_connected():
                await player.connect(interaction.user.voice.channel)
            
            # Message de chargement
            await interaction.response.defer()
            loading_msg = await interaction.followup.send(embed=MusicEmbeds.info(
                f"⏳ Chargement de la playlist **{name}**...",
                "Chargement"
            ))
            
            # Ajouter toutes les pistes à la queue
            added_count = 0
            for pl_track in playlist.tracks:
                # Rechercher la piste pour obtenir les métadonnées complètes
                track = await player.youtube_source.search(pl_track.url, interaction.user)
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
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors du chargement de la playlist."
            ))
    
    @app_commands.command(name="list_playlists", description="Liste toutes les playlists")
    async def list_playlists(self, interaction: discord.Interaction):
        """
        Liste toutes les playlists du serveur
        
        Usage: !list_playlists
        """
        try:
            playlists = await self.db.get_playlists_by_guild(interaction.guild.id)
            
            if not playlists:
                await interaction.response.send_message(embed=MusicEmbeds.info(
                    "Aucune playlist sauvegardée sur ce serveur."
                ))
                return
            
            # Créer l'embed
            embed = discord.Embed(
                title=f"📋 Playlists de {interaction.guild.name}",
                color=MusicEmbeds.info("").color
            )
            
            for playlist in playlists[:25]:  # Limiter à 25 pour ne pas dépasser la limite Discord
                owner = interaction.guild.get_member(playlist.owner_id)
                owner_name = owner.display_name if owner else "Inconnu"
                
                value = f"👤 {owner_name} • {playlist.track_count} piste(s) • {playlist.duration_formatted}"
                embed.add_field(
                    name=playlist.name,
                    value=value,
                    inline=False
                )
            
            if len(playlists) > 25:
                embed.set_footer(text=f"... et {len(playlists) - 25} autres playlists")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des playlists: {e}")
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la récupération des playlists."
            ))
    
    @app_commands.command(name="remove_playlist", description="Supprime une playlist")
    @app_commands.describe(name="Nom de la playlist")
    async def remove_playlist(self, interaction: discord.Interaction, *, name: str):
        """
        Supprime une playlist
        
        Usage: !remove_playlist <nom>
        """
        try:
            # Récupérer la playlist
            playlist = await self.db.get_playlist_by_name(name, interaction.guild.id)
            
            if not playlist:
                await interaction.response.send_message(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            # Vérifier que l'utilisateur est le propriétaire ou a les permissions
            if playlist.owner_id != interaction.user.id and not interaction.user.guild_permissions.manage_guild:
                await interaction.response.send_message(embed=MusicEmbeds.error(
                    "Vous n'avez pas la permission de supprimer cette playlist."
                ))
                return
            
            # Supprimer la playlist
            await self.db.delete_playlist(playlist.id)
            
            await interaction.response.send_message(embed=MusicEmbeds.success(
                f"🗑️ Playlist **{name}** supprimée."
            ))
            logger.info(f"Playlist supprimée: {name}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la playlist: {e}")
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la suppression de la playlist."
            ))
    
    @app_commands.command(name="playlist_info", description="Affiche les détails d'une playlist")
    @app_commands.describe(name="Nom de la playlist")
    async def playlist_info(self, interaction: discord.Interaction, *, name: str):
        """
        Affiche les détails d'une playlist
        
        Usage: !playlist_info <nom>
        """
        try:
            playlist = await self.db.get_playlist_by_name(name, interaction.guild.id)
            
            if not playlist:
                await interaction.response.send_message(embed=MusicEmbeds.error(
                    f"Playlist '{name}' introuvable."
                ))
                return
            
            owner = interaction.guild.get_member(playlist.owner_id)
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
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'affichage de la playlist: {e}")
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de l'affichage de la playlist."
            ))
    
    @app_commands.command(name="save_spotify_playlist", description="Importe une playlist Spotify")
    @app_commands.describe(url="URL Spotify (playlist ou album)", name="Nom de la playlist")
    async def save_spotify_playlist(self, interaction: discord.Interaction, url: str, *, name: str):
        """
        Crée une playlist depuis un lien Spotify (playlist ou album)
        
        Usage: !save_spotify_playlist <url_spotify> <nom>
        """
        player = self._get_player(interaction)
        
        # Vérifier que c'est une URL Spotify
        if not player.spotify_source.is_spotify_url(url):
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Veuillez fournir une URL Spotify valide (playlist ou album)."
            ))
            return
        
        if not player.spotify_source.is_available():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "L'intégration Spotify n'est pas configurée."
            ))
            return
        
        # Message de chargement
        await interaction.response.defer()
        loading_msg = await interaction.followup.send(embed=MusicEmbeds.info(
            f"⏳ Importation depuis Spotify...",
            "Chargement"
        ))
        
        try:
            # Déterminer le type de lien Spotify
            result = player.spotify_source.extract_id_from_url(url)
            if not result:
                await loading_msg.edit(embed=MusicEmbeds.error(
                    "URL Spotify invalide."
                ))
                return
            
            spotify_type, spotify_id = result
            
            # Seules les playlists et albums sont supportés
            if spotify_type not in ['playlist', 'album']:
                await loading_msg.edit(embed=MusicEmbeds.error(
                    "Seules les playlists et albums Spotify sont supportés."
                ))
                return
            
            # Récupérer les pistes Spotify
            if spotify_type == 'playlist':
                spotify_tracks = await player.spotify_source.get_playlist(url)
            else:
                spotify_tracks = await player.spotify_source.get_album(url)
            
            if not spotify_tracks:
                await loading_msg.edit(embed=MusicEmbeds.error(
                    f"Impossible de charger la {spotify_type} Spotify."
                ))
                return
            
            # Créer la playlist dans la base de données
            playlist = await self.db.create_playlist(
                name=name,
                guild_id=interaction.guild.id,
                owner_id=interaction.user.id
            )
            
            # Convertir et ajouter toutes les pistes
            added_count = 0
            for spotify_track in spotify_tracks[:100]:  # Limiter à 100 pistes
                # Rechercher sur YouTube pour obtenir l'URL
                track = await player.youtube_source.search(spotify_track.search_query, interaction.user)
                if track:
                    track.source = 'spotify'
                    await self.db.add_track_to_playlist(playlist.id, track)
                    added_count += 1
            
            # Récupérer la playlist mise à jour
            playlist = await self.db.get_playlist(playlist.id)
            
            embed = discord.Embed(
                title="✅ Playlist Spotify importée",
                description=f"**{name}**",
                color=MusicEmbeds.success("").color
            )
            embed.add_field(name="Pistes", value=str(added_count), inline=True)
            embed.add_field(name="Durée", value=playlist.duration_formatted, inline=True)
            embed.add_field(name="Source", value="Spotify", inline=True)
            
            await loading_msg.edit(embed=embed)
            logger.info(f"Playlist Spotify importée: {name} ({added_count} pistes)")
            
        except ValueError as e:
            await loading_msg.edit(embed=MusicEmbeds.error(str(e)))
        except Exception as e:
            logger.error(f"Erreur lors de l'importation de la playlist Spotify: {e}")
            await loading_msg.edit(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de l'importation de la playlist Spotify."
            ))


async def setup(bot):
    """Fonction requise pour charger le cog"""
    await bot.add_cog(PlaylistCog(bot))
