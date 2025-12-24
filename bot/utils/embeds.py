"""Générateur d'embeds Discord pour les messages du bot"""

import discord
from typing import List, Optional
from bot.config import Config
from bot.audio.track import Track
from bot.audio.queue import MusicQueue


class MusicEmbeds:
    """Générateur d'embeds Discord formatés pour la musique"""
    
    @staticmethod
    def now_playing(track: Track) -> discord.Embed:
        """
        Crée un embed pour la piste en cours de lecture
        
        Args:
            track: Piste actuellement jouée
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title="🎵 Lecture en cours",
            description=f"**{track.title}**",
            color=Config.COLOR_PRIMARY
        )
        
        embed.add_field(
            name="Durée",
            value=track.duration_formatted,
            inline=True
        )
        
        embed.add_field(
            name="Demandé par",
            value=track.requester.mention,
            inline=True
        )
        
        embed.add_field(
            name="Source",
            value=track.source.capitalize(),
            inline=True
        )
        
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        if track.url:
            embed.add_field(
                name="Lien",
                value=f"[Cliquez ici]({track.url})",
                inline=False
            )
        
        return embed
    
    @staticmethod
    def added_to_queue(track: Track, position: int) -> discord.Embed:
        """
        Crée un embed pour une piste ajoutée à la queue
        
        Args:
            track: Piste ajoutée
            position: Position dans la queue
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title="✅ Ajouté à la file d'attente",
            description=f"**{track.title}**",
            color=Config.COLOR_SUCCESS
        )
        
        embed.add_field(
            name="Position",
            value=f"#{position}",
            inline=True
        )
        
        embed.add_field(
            name="Durée",
            value=track.duration_formatted,
            inline=True
        )
        
        embed.add_field(
            name="Demandé par",
            value=track.requester.mention,
            inline=True
        )
        
        if track.thumbnail:
            embed.set_thumbnail(url=track.thumbnail)
        
        return embed
    
    @staticmethod
    async def queue_list(queue: MusicQueue, current: Optional[Track] = None, page: int = 1) -> discord.Embed:
        """
        Crée un embed pour afficher la file d'attente
        
        Args:
            queue: File d'attente musicale
            current: Piste actuellement jouée (optionnel)
            page: Numéro de page (10 pistes par page)
            
        Returns:
            Embed Discord formaté
        """
        tracks = await queue.get_list()
        total_tracks = len(tracks)
        
        if total_tracks == 0 and not current:
            embed = discord.Embed(
                title="📋 File d'attente",
                description="La file d'attente est vide.",
                color=Config.COLOR_INFO
            )
            return embed
        
        # Pagination
        items_per_page = 10
        start_idx = (page - 1) * items_per_page
        end_idx = start_idx + items_per_page
        page_tracks = tracks[start_idx:end_idx]
        total_pages = (total_tracks + items_per_page - 1) // items_per_page
        
        # Construction de la description
        description = ""
        
        if current:
            description += f"**🎵 En cours:**\n{current.title} - `{current.duration_formatted}`\n\n"
        
        if page_tracks:
            description += "**📋 À venir:**\n"
            for idx, track in enumerate(page_tracks, start=start_idx + 1):
                description += f"`{idx}.` {track.title} - `{track.duration_formatted}`\n"
        
        embed = discord.Embed(
            title="📋 File d'attente",
            description=description,
            color=Config.COLOR_INFO
        )
        
        # Calculer la durée totale
        total_duration = sum(track.duration for track in tracks)
        if current:
            total_duration += current.duration
        
        minutes, seconds = divmod(total_duration, 60)
        hours, minutes = divmod(minutes, 60)
        
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
        
        embed.set_footer(
            text=f"Page {page}/{max(1, total_pages)} • {total_tracks} piste(s) • Durée totale: {duration_str}"
        )
        
        return embed
    
    @staticmethod
    def error(message: str, title: str = "❌ Erreur") -> discord.Embed:
        """
        Crée un embed d'erreur
        
        Args:
            message: Message d'erreur
            title: Titre de l'embed
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title=title,
            description=message,
            color=Config.COLOR_ERROR
        )
        return embed
    
    @staticmethod
    def success(message: str, title: str = "✅ Succès") -> discord.Embed:
        """
        Crée un embed de succès
        
        Args:
            message: Message de succès
            title: Titre de l'embed
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title=title,
            description=message,
            color=Config.COLOR_SUCCESS
        )
        return embed
    
    @staticmethod
    def info(message: str, title: str = "ℹ️ Information") -> discord.Embed:
        """
        Crée un embed d'information
        
        Args:
            message: Message d'information
            title: Titre de l'embed
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title=title,
            description=message,
            color=Config.COLOR_INFO
        )
        return embed
    
    @staticmethod
    def warning(message: str, title: str = "⚠️ Attention") -> discord.Embed:
        """
        Crée un embed d'avertissement
        
        Args:
            message: Message d'avertissement
            title: Titre de l'embed
            
        Returns:
            Embed Discord formaté
        """
        embed = discord.Embed(
            title=title,
            description=message,
            color=Config.COLOR_WARNING
        )
        return embed
