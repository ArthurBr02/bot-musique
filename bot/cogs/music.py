"""Cog de commandes musicales pour le bot Discord"""

import logging
from typing import Optional
import discord
from discord.ext import commands

from bot.audio.player import MusicPlayer
from bot.utils.embeds import MusicEmbeds
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
    
    def _get_player(self, ctx: commands.Context) -> MusicPlayer:
        """Récupère le player pour le serveur actuel"""
        return self.bot.get_player(ctx.guild)
    
    async def _ensure_voice(self, ctx: commands.Context) -> bool:
        """
        Vérifie que l'utilisateur et le bot sont dans un canal vocal
        
        Returns:
            True si tout est OK
            
        Raises:
            NotInVoiceChannel: Si l'utilisateur n'est pas dans un canal vocal
            ConnectionTimeout: Si la connexion au canal vocal timeout
        """
        # Vérifier que l'utilisateur est dans un canal vocal
        if not ctx.author.voice:
            raise NotInVoiceChannel()
        
        # Vérifier que le bot peut se connecter
        player = self._get_player(ctx)
        if not player.is_connected():
            # Connecter le bot au canal de l'utilisateur
            # ConnectionTimeout sera propagée si timeout
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
        Joue une musique depuis YouTube/Spotify ou l'ajoute à la queue
        
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
            # Vérifier si c'est une URL Spotify
            if player.spotify_source.is_spotify_url(query):
                if not player.spotify_source.is_available():
                    await loading_msg.edit(embed=MusicEmbeds.error(
                        "L'intégration Spotify n'est pas configurée. Veuillez configurer SPOTIFY_CLIENT_ID et SPOTIFY_CLIENT_SECRET."
                    ))
                    return
                
                # Déterminer le type de lien Spotify
                result = player.spotify_source.extract_id_from_url(query)
                if not result:
                    await loading_msg.edit(embed=MusicEmbeds.error(
                        "URL Spotify invalide."
                    ))
                    return
                
                spotify_type, spotify_id = result
                
                # Traiter selon le type
                if spotify_type == 'track':
                    # Piste unique
                    spotify_track = await player.spotify_source.get_track(query)
                    if not spotify_track:
                        await loading_msg.edit(embed=MusicEmbeds.error(
                            "Impossible de récupérer la piste Spotify."
                        ))
                        return
                    
                    # Convertir en recherche YouTube
                    await loading_msg.edit(embed=MusicEmbeds.info(
                        f"🎵 Conversion Spotify → YouTube: `{spotify_track.search_query}`...",
                        "Chargement"
                    ))
                    
                    track = await player.youtube_source.search(spotify_track.search_query, ctx.author)
                    if not track:
                        await loading_msg.edit(embed=MusicEmbeds.error(
                            f"Impossible de trouver sur YouTube: `{spotify_track.search_query}`"
                        ))
                        return
                    
                    # Mettre à jour la source pour indiquer Spotify
                    track.source = 'spotify'
                    
                    # Ajouter à la queue
                    position = await player.add_track(track)
                    
                    if position == 1 and not player.is_playing():
                        await loading_msg.edit(embed=MusicEmbeds.now_playing(track))
                    else:
                        await loading_msg.edit(embed=MusicEmbeds.added_to_queue(track, position))
                
                elif spotify_type in ['playlist', 'album']:
                    # Playlist ou album
                    type_name = "playlist" if spotify_type == 'playlist' else "album"
                    await loading_msg.edit(embed=MusicEmbeds.info(
                        f"📋 Chargement de la {type_name} Spotify...",
                        "Chargement"
                    ))
                    
                    if spotify_type == 'playlist':
                        spotify_tracks = await player.spotify_source.get_playlist(query)
                    else:
                        spotify_tracks = await player.spotify_source.get_album(query)
                    
                    if not spotify_tracks:
                        await loading_msg.edit(embed=MusicEmbeds.error(
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
                        
                        track = await player.youtube_source.search(spotify_track.search_query, ctx.author)
                        if track:
                            track.source = 'spotify'
                            await player.add_track(track)
                            added_count += 1
                    
                    if added_count > 0:
                        await loading_msg.edit(embed=MusicEmbeds.success(
                            f"✅ {added_count} piste(s) ajoutée(s) depuis la {type_name} Spotify.",
                            f"{type_name.capitalize()} chargée"
                        ))
                    else:
                        await loading_msg.edit(embed=MusicEmbeds.warning(
                            "Chargement interrompu.",
                            "Annulé"
                        ))
            
            else:
                # Recherche YouTube normale
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
        player = self._get_player(ctx)
        
        try:
            player.set_volume(volume / 100)
            await ctx.send(embed=MusicEmbeds.success(
                f"🔊 Volume réglé à {volume}%."
            ))
        except InvalidVolume as e:
            await ctx.send(embed=MusicEmbeds.error(
                e.message
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
