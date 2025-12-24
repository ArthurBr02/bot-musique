"""Vues Discord interactives pour le bot musical"""

import discord
from discord.ui import View, Button
from typing import Optional
import asyncio


class MusicControlView(View):
    """Vue avec boutons de contrôle de lecture"""
    
    def __init__(self, player, timeout=300):
        super().__init__(timeout=timeout)
        self.player = player
        self.message: Optional[discord.Message] = None
    
    @discord.ui.button(label="⏯️", style=discord.ButtonStyle.primary)
    async def play_pause_button(self, interaction: discord.Interaction, button: Button):
        """Bouton play/pause"""
        if self.player.voice_client and self.player.voice_client.is_playing():
            await self.player.pause()
            await interaction.response.send_message("⏸️ Lecture en pause", ephemeral=True)
        elif self.player.voice_client and self.player.voice_client.is_paused():
            await self.player.resume()
            await interaction.response.send_message("▶️ Lecture reprise", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
    
    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.primary)
    async def skip_button(self, interaction: discord.Interaction, button: Button):
        """Bouton skip"""
        if await self.player.skip():
            await interaction.response.send_message("⏭️ Piste passée", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Aucune musique en cours", ephemeral=True)
    
    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: Button):
        """Bouton stop"""
        await self.player.stop()
        await interaction.response.send_message("⏹️ Lecture arrêtée", ephemeral=True)
        self.stop()
    
    @discord.ui.button(label="🔊+", style=discord.ButtonStyle.secondary)
    async def volume_up_button(self, interaction: discord.Interaction, button: Button):
        """Bouton augmenter volume"""
        new_volume = min(1.0, self.player.volume + 0.1)
        self.player.set_volume(new_volume)
        await interaction.response.send_message(
            f"🔊 Volume: {int(new_volume * 100)}%", 
            ephemeral=True
        )
    
    @discord.ui.button(label="🔉-", style=discord.ButtonStyle.secondary)
    async def volume_down_button(self, interaction: discord.Interaction, button: Button):
        """Bouton diminuer volume"""
        new_volume = max(0.0, self.player.volume - 0.1)
        self.player.set_volume(new_volume)
        await interaction.response.send_message(
            f"🔉 Volume: {int(new_volume * 100)}%", 
            ephemeral=True
        )
    
    @discord.ui.button(label="👋", style=discord.ButtonStyle.danger)
    async def disconnect_button(self, interaction: discord.Interaction, button: Button):
        """Bouton déconnexion"""
        await self.player.disconnect()
        await interaction.response.send_message("👋 Déconnecté", ephemeral=True)
        self.stop()
    
    async def on_timeout(self):
        """Désactive les boutons après timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass


class QueuePaginationView(View):
    """Vue avec pagination pour la queue"""
    
    def __init__(self, embeds: list, timeout=120):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.message: Optional[discord.Message] = None
        self._update_buttons()
    
    def _update_buttons(self):
        """Met à jour l'état des boutons"""
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= len(self.embeds) - 1
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: Button):
        """Bouton page précédente"""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page],
                view=self
            )
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: Button):
        """Bouton page suivante"""
        if self.current_page < len(self.embeds) - 1:
            self.current_page += 1
            self._update_buttons()
            await interaction.response.edit_message(
                embed=self.embeds[self.current_page],
                view=self
            )
    
    async def on_timeout(self):
        """Désactive les boutons après timeout"""
        if self.message:
            try:
                for item in self.children:
                    item.disabled = True
                await self.message.edit(view=self)
            except:
                pass
