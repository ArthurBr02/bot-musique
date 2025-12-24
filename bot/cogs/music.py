"""Cog de commandes musicales pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from bot.audio.player import MusicPlayer
from bot.utils.embeds import MusicEmbeds, create_progress_bar
from bot.utils.views import MusicControlView, QueuePaginationView
from bot.utils.exceptions import (
    NotInVoiceChannel,
    BotNotConnected,
    TrackNotFound,
    ConnectionTimeout,
    InvalidVolume
)

logger = logging.getLogger(__name__)


class Music(commands.Cog):
    """Commandes de lecture musicale"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def _get_player(self, interaction: discord.Interaction) -> MusicPlayer:
        """Récupère le player pour le serveur actuel"""
        return self.bot.get_player(interaction.guild)
    
    async def _ensure_voice(self, interaction: discord.Interaction) -> bool:
        """
        Vérifie que l'utilisateur et le bot sont dans un canal vocal
        
        Returns:
            True si tout est OK
            
        Raises:
            NotInVoiceChannel: Si l'utilisateur n'est pas dans un canal vocal
            ConnectionTimeout: Si la connexion au canal vocal timeout
        """
        # Vérifier que l'utilisateur est dans un canal vocal
        if not interaction.user.voice:
            raise NotInVoiceChannel()
        
        # Vérifier que le bot peut se connecter
        player = self._get_player(interaction)
        if not player.is_connected():
            # Connecter le bot au canal de l'utilisateur
            # ConnectionTimeout sera propagée si timeout
            success = await player.connect(interaction.user.voice.channel)
            if not success:
                await interaction.response.send_message(
                    embed=MusicEmbeds.error("Impossible de se connecter au canal vocal."),
                    ephemeral=True
                )
                return False
        
        return True
    
    @app_commands.command(name="help", description="Affiche l'aide et la liste des commandes")
    async def help(self, interaction: discord.Interaction):
        """Affiche l'aide pour utiliser le bot"""
        embed = discord.Embed(
            title="🎵 Bot Musical - Aide",
            description="Voici comment utiliser les commandes slash :",
            color=MusicEmbeds.info("").color
        )
        
        embed.add_field(
            name="📖 Comment utiliser les commandes",
            value="Tapez `/` dans le chat pour voir toutes les commandes disponibles.\n"
                  "Discord vous montrera automatiquement les paramètres requis et leur description.",
            inline=False
        )
        
        embed.add_field(
            name="🎵 Commandes Musicales",
            value="`/play` - Joue une musique\n"
                  "`/pause` - Met en pause\n"
                  "`/resume` - Reprend la lecture\n"
                  "`/skip` - Passe à la piste suivante\n"
                  "`/stop` - Arrête et vide la queue\n"
                  "`/queue` - Affiche la file d'attente\n"
                  "`/nowplaying` - Piste en cours\n"
                  "`/volume` - Règle le volume\n"
                  "`/loop` - Active/désactive la répétition\n"
                  "`/shuffle` - Mélange la queue\n"
                  "`/clear` - Vide la queue\n"
                  "`/remove` - Retire une piste\n"
                  "`/move` - Déplace une piste\n"
                  "`/disconnect` - Déconnecte le bot",
            inline=False
        )
        
        embed.add_field(
            name="📋 Commandes Playlist",
            value="`/save_playlist` - Sauvegarde la queue\n"
                  "`/load_playlist` - Charge une playlist\n"
                  "`/list_playlists` - Liste les playlists\n"
                  "`/playlist_info` - Détails d'une playlist\n"
                  "`/remove_playlist` - Supprime une playlist\n"
                  "`/save_spotify_playlist` - Importe depuis Spotify",
            inline=False
        )
        
        embed.set_footer(text="💡 Astuce : Utilisez l'auto-complétion pour voir les paramètres de chaque commande")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    
    @app_commands.command(name="play", description="Joue une musique depuis YouTube/Spotify")
    @app_commands.describe(query="URL YouTube/Spotify ou terme de recherche")
    async def play(self, interaction: discord.Interaction, query: str):
        """Joue une musique depuis YouTube/Spotify ou l'ajoute à la queue"""
        # Vérifier les conditions vocales
        if not await self._ensure_voice(interaction):
            return
        
        player = self._get_player(interaction)
        
        # Defer la réponse car la recherche peut prendre du temps
        await interaction.response.defer()
        
        try:
            # Vérifier si c'est une URL Spotify
            if player.spotify_source.is_spotify_url(query):
                if not player.spotify_source.is_available():
                    await interaction.followup.send(embed=MusicEmbeds.error(
                        "L'intégration Spotify n'est pas configurée. Veuillez configurer SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET."
                    ))
                    return
                
                # Déterminer le type de lien Spotify
                result = player.spotify_source.extract_id_from_url(query)
                if not result:
                    await interaction.followup.send(embed=MusicEmbeds.error(
                        "URL Spotify invalide."
                    ))
                    return
                
                spotify_type, spotify_id = result
                
                # Traiter selon le type
                if spotify_type == 'track':
                    # Piste unique
                    spotify_track = await player.spotify_source.get_track(query)
                    if not spotify_track:
                        await interaction.followup.send(embed=MusicEmbeds.error(
                            "Impossible de récupérer la piste Spotify."
                        ))
                        return
                    
                    # Convertir en recherche YouTube
                    track = await player.youtube_source.search(spotify_track.search_query, interaction.user)
                    if not track:
                        await interaction.followup.send(embed=MusicEmbeds.error(
                            f"Impossible de trouver sur YouTube: `{spotify_track.search_query}`"
                        ))
                        return
                    
                    # Mettre à jour la source pour indiquer Spotify
                    track.source = 'spotify'
                    
                    # Ajouter à la queue
                    position = await player.add_track(track)
                    
                    if position == 1 and not player.is_playing():
                        await interaction.followup.send(embed=MusicEmbeds.now_playing(track))
                    else:
                        await interaction.followup.send(embed=MusicEmbeds.added_to_queue(track, position))
                
                elif spotify_type in ['playlist', 'album']:
                    # Playlist ou album
                    type_name = "playlist" if spotify_type == 'playlist' else "album"
                    
                    if spotify_type == 'playlist':
                        spotify_tracks = await player.spotify_source.get_playlist(query)
                    else:
                        spotify_tracks = await player.spotify_source.get_album(query)
                    
                    if not spotify_tracks:
                        await interaction.followup.send(embed=MusicEmbeds.error(
                            f"Impossible de charger la {type_name} Spotify."
                        ))
                        return
                    
                    # Convertir et ajouter toutes les pistes
                    added_count = 0
                    for spotify_track in spotify_tracks[:50]:  # Limiter à 50 pistes
                        # Vérifier si le player est toujours connecté
                        if not player.is_connected():
                            logger.info(f"Chargement de playlist interrompu (déconnexion) après {added_count} pistes")
                            break
                        
                        track = await player.youtube_source.search(spotify_track.search_query, interaction.user)
                        if track:
                            track.source = 'spotify'
                            await player.add_track(track)
                            added_count += 1
                    
                    if added_count > 0:
                        await interaction.followup.send(embed=MusicEmbeds.success(
                            f"✅ {added_count} piste(s) ajoutée(s) depuis la {type_name} Spotify.",
                            f"{type_name.capitalize()} chargée"
                        ))
                    else:
                        await interaction.followup.send(embed=MusicEmbeds.warning(
                            "Chargement interrompu.",
                            "Annulé"
                        ))
            
            else:
                # Recherche YouTube normale
                track = await player.youtube_source.search(query, interaction.user)
                
                if not track:
                    await interaction.followup.send(embed=MusicEmbeds.error(
                        f"Aucun résultat trouvé pour: `{query}`"
                    ))
                    return
                
                # Ajouter à la queue
                position = await player.add_track(track)
                
                # Si c'est la seule piste et que rien ne joue, elle va démarrer automatiquement
                if position == 1 and not player.is_playing():
                    await interaction.followup.send(embed=MusicEmbeds.now_playing(track))
                else:
                    await interaction.followup.send(embed=MusicEmbeds.added_to_queue(track, position))
            
        except Exception as e:
            logger.error(f"Erreur lors de la lecture: {e}")
            await interaction.followup.send(embed=MusicEmbeds.error(
                "Une erreur s'est produite lors de la recherche."
            ))
    
    @app_commands.command(name="pause", description="Met en pause la lecture en cours")
    async def pause(self, interaction: discord.Interaction):
        """Met en pause la lecture en cours"""
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Le bot n'est pas connecté à un canal vocal."),
                ephemeral=True
            )
            return
        
        if await player.pause():
            await interaction.response.send_message(
                embed=MusicEmbeds.success("⏸️ Lecture mise en pause.")
            )
        else:
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Aucune musique n'est en cours de lecture."),
                ephemeral=True
            )
    
    @app_commands.command(name="resume", description="Reprend la lecture en pause")
    async def resume(self, interaction: discord.Interaction):
        """Reprend la lecture en pause"""
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Le bot n'est pas connecté à un canal vocal."),
                ephemeral=True
            )
            return
        
        if await player.resume():
            await interaction.response.send_message(
                embed=MusicEmbeds.success("▶️ Lecture reprise.")
            )
        else:
            await interaction.response.send_message(
                embed=MusicEmbeds.error("La lecture n'est pas en pause."),
                ephemeral=True
            )
    
    @app_commands.command(name="skip", description="Passe à la piste suivante")
    async def skip(self, interaction: discord.Interaction):
        """Passe à la piste suivante"""
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Le bot n'est pas connecté à un canal vocal."),
                ephemeral=True
            )
            return
        
        if await player.skip():
            await interaction.response.send_message(
                embed=MusicEmbeds.success("⏭️ Piste passée.")
            )
        else:
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Aucune musique n'est en cours de lecture."),
                ephemeral=True
            )
    
    @app_commands.command(name="stop", description="Arrête la lecture et vide la queue")
    async def stop(self, interaction: discord.Interaction):
        """Arrête la lecture et vide la queue"""
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(
                embed=MusicEmbeds.error("Le bot n'est pas connecté à un canal vocal."),
                ephemeral=True
            )
            return
        
        await player.stop()
        await interaction.response.send_message(
            embed=MusicEmbeds.success("⏹️ Lecture arrêtée et file d'attente vidée.")
        )
    
    @app_commands.command(name="queue", description="Affiche la file d'attente")
    @app_commands.describe(page="Numéro de page (optionnel)")
    async def queue(self, interaction: discord.Interaction, page: int = 1):
        """
        Affiche la file d'attente avec pagination interactive
        
        Usage: !queue [page]
        """
        player = self._get_player(interaction)
        
        # Calculer le nombre total de pages
        queue_size = await player.queue.size()
        items_per_page = 10
        total_pages = max(1, (queue_size + items_per_page - 1) // items_per_page)
        
        # Créer les embeds pour toutes les pages
        embeds = []
        for p in range(1, total_pages + 1):
            embed = await MusicEmbeds.queue_list(
                player.queue,
                player.current,
                p
            )
            embeds.append(embed)
        
        # Si une seule page, pas besoin de pagination
        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0])
        else:
            # Créer la vue avec pagination
            view = QueuePaginationView(embeds)
            view.current_page = max(0, min(page - 1, len(embeds) - 1))
            view._update_buttons()
            message = await interaction.response.send_message(embed=embeds[view.current_page], view=view)
            view.message = message
    
    @app_commands.command(name="nowplaying", description="Affiche la piste en cours")
    async def nowplaying(self, interaction: discord.Interaction):
        """
        Affiche la piste en cours de lecture avec contrôles interactifs
        
        Usage: !nowplaying
        """
        player = self._get_player(interaction)
        
        if not player.current:
            await interaction.response.send_message(embed=MusicEmbeds.info(
                "Aucune musique n'est en cours de lecture."
            ))
            return
        
        # Créer la barre de progression
        current_pos = player.get_current_position()
        progress_bar = create_progress_bar(current_pos, player.current.duration)
        
        # Créer l'embed avec la barre de progression
        embed = MusicEmbeds.now_playing(
            player.current,
            progress_bar=progress_bar,
            loop_enabled=player.loop
        )
        
        # Créer la vue avec les boutons de contrôle
        view = MusicControlView(player)
        message = await interaction.response.send_message(embed=embed, view=view)
        view.message = message
    
    @app_commands.command(name="volume", description="Règle le volume (0-100)")
    @app_commands.describe(volume="Niveau de volume (0-100)")
    async def volume(self, interaction: discord.Interaction, volume: int):
        """
        Règle le volume de lecture (0-100)
        
        Usage: !volume <0-100>
        """
        player = self._get_player(interaction)
        
        try:
            player.set_volume(volume / 100)
            await interaction.response.send_message(embed=MusicEmbeds.success(
                f"🔊 Volume réglé à {volume}%."
            ))
        except InvalidVolume as e:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                e.message
            ))
    
    @app_commands.command(name="disconnect", description="Déconnecte le bot du canal vocal")
    async def disconnect(self, interaction: discord.Interaction):
        """
        Déconnecte le bot du canal vocal
        
        Usage: !disconnect
        """
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        await player.disconnect()
        await interaction.response.send_message(embed=MusicEmbeds.success(
            "👋 Déconnecté du canal vocal."
        ))
    
    @app_commands.command(name="loop", description="Active/désactive la répétition")
    async def loop(self, interaction: discord.Interaction):
        """
        Active/désactive la répétition de la piste actuelle
        
        Usage: !loop
        """
        player = self._get_player(interaction)
        player.loop = not player.loop
        
        status = "activée" if player.loop else "désactivée"
        emoji = "🔁" if player.loop else "➡️"
        
        await interaction.response.send_message(embed=MusicEmbeds.success(
            f"{emoji} Répétition {status}."
        ))
    
    @app_commands.command(name="shuffle", description="Mélange la file d'attente")
    async def shuffle(self, interaction: discord.Interaction):
        """
        Mélange aléatoirement la file d'attente
        
        Usage: !shuffle
        """
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        queue_size = await player.queue.size()
        if queue_size == 0:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "La file d'attente est vide."
            ))
            return
        
        await player.queue.shuffle()
        await interaction.response.send_message(embed=MusicEmbeds.success(
            f"🔀 File d'attente mélangée ({queue_size} piste(s))."
        ))
    
    @app_commands.command(name="clear", description="Vide la file d'attente")
    async def clear(self, interaction: discord.Interaction):
        """
        Vide la file d'attente sans arrêter la lecture en cours
        
        Usage: !clear
        """
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        queue_size = await player.queue.size()
        if queue_size == 0:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "La file d'attente est déjà vide."
            ))
            return
        
        await player.clear_queue()
        await interaction.response.send_message(embed=MusicEmbeds.success(
            f"🗑️ File d'attente vidée ({queue_size} piste(s) retirée(s))."
        ))
    
    @app_commands.command(name="remove", description="Retire une piste")
    @app_commands.describe(position="Position de la piste à retirer")
    async def remove(self, interaction: discord.Interaction, position: int):
        """
        Retire une piste de la file d'attente
        
        Usage: !remove <position>
        """
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        removed_track = await player.queue.remove(position)
        
        if removed_track:
            await interaction.response.send_message(embed=MusicEmbeds.success(
                f"🗑️ Piste retirée de la position {position}:\n`{removed_track.title}`"
            ))
        else:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                f"Position invalide: {position}. Utilisez `!queue` pour voir les positions."
            ))
    
    @app_commands.command(name="move", description="Déplace une piste")
    @app_commands.describe(from_pos="Position actuelle", to_pos="Nouvelle position")
    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):
        """
        Déplace une piste dans la file d'attente
        
        Usage: !move <position_actuelle> <nouvelle_position>
        """
        player = self._get_player(interaction)
        
        if not player.is_connected():
            await interaction.response.send_message(embed=MusicEmbeds.error(
                "Le bot n'est pas connecté à un canal vocal."
            ))
            return
        
        moved_track = await player.queue.move(from_pos, to_pos)
        
        if moved_track:
            await interaction.response.send_message(embed=MusicEmbeds.success(
                f"↔️ Piste déplacée de la position {from_pos} à {to_pos}:\n`{moved_track.title}`"
            ))
        else:
            await interaction.response.send_message(embed=MusicEmbeds.error(
                f"Positions invalides: {from_pos} → {to_pos}. Utilisez `!queue` pour voir les positions."
            ))


async def setup(bot):
    """Fonction requise pour charger le cog"""
    await bot.add_cog(Music(bot))
