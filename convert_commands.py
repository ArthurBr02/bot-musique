"""Script pour convertir les commandes restantes en slash commands"""
import re

# Lire le fichier
with open(r'u:\Projets\Git\ba-tbot-v2\bot\cogs\music.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Définir les remplacements
replacements = [
    # queue command
    (
        r"@commands\.command\(name='queue', aliases=\['q'\]\)\s+async def queue\(self, ctx: commands\.Context, page: int = 1\):",
        '@app_commands.command(name="queue", description="Affiche la file d\'attente")\n    @app_commands.describe(page="Numéro de page (optionnel)")\n    async def queue(self, interaction: discord.Interaction, page: int = 1):'
    ),
    # nowplaying command
    (
        r"@commands\.command\(name='nowplaying', aliases=\['np', 'current'\]\)\s+async def nowplaying\(self, ctx: commands\.Context\):",
        '@app_commands.command(name="nowplaying", description="Affiche la piste en cours")\n    async def nowplaying(self, interaction: discord.Interaction):'
    ),
    # volume command
    (
        r"@commands\.command\(name='volume', aliases=\['vol', 'v'\]\)\s+async def volume\(self, ctx: commands\.Context, volume: int\):",
        '@app_commands.command(name="volume", description="Règle le volume (0-100)")\n    @app_commands.describe(volume="Niveau de volume (0-100)")\n    async def volume(self, interaction: discord.Interaction, volume: int):'
    ),
    # disconnect command
    (
        r"@commands\.command\(name='disconnect', aliases=\['dc', 'leave'\]\)\s+async def disconnect\(self, ctx: commands\.Context\):",
        '@app_commands.command(name="disconnect", description="Déconnecte le bot du canal vocal")\n    async def disconnect(self, interaction: discord.Interaction):'
    ),
    # loop command
    (
        r"@commands\.command\(name='loop', aliases=\['repeat'\]\)\s+async def loop\(self, ctx: commands\.Context\):",
        '@app_commands.command(name="loop", description="Active/désactive la répétition")\n    async def loop(self, interaction: discord.Interaction):'
    ),
    # shuffle command
    (
        r"@commands\.command\(name='shuffle'\)\s+async def shuffle\(self, ctx: commands\.Context\):",
        '@app_commands.command(name="shuffle", description="Mélange la file d\'attente")\n    async def shuffle(self, interaction: discord.Interaction):'
    ),
    # clear command
    (
        r"@commands\.command\(name='clear'\)\s+async def clear\(self, ctx: commands\.Context\):",
        '@app_commands.command(name="clear", description="Vide la file d\'attente")\n    async def clear(self, interaction: discord.Interaction):'
    ),
    # remove command
    (
        r"@commands\.command\(name='remove', aliases=\['rm'\]\)\s+async def remove\(self, ctx: commands\.Context, position: int\):",
        '@app_commands.command(name="remove", description="Retire une piste")\n    @app_commands.describe(position="Position de la piste à retirer")\n    async def remove(self, interaction: discord.Interaction, position: int):'
    ),
    # move command
    (
        r"@commands\.command\(name='move', aliases=\['mv'\]\)\s+async def move\(self, ctx: commands\.Context, from_pos: int, to_pos: int\):",
        '@app_commands.command(name="move", description="Déplace une piste")\n    @app_commands.describe(from_pos="Position actuelle", to_pos="Nouvelle position")\n    async def move(self, interaction: discord.Interaction, from_pos: int, to_pos: int):'
    ),
]

# Appliquer les remplacements de décorateurs
for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Remplacer ctx par interaction dans les fonctions restantes
content = re.sub(r'player = self\._get_player\(ctx\)', 'player = self._get_player(interaction)', content)
content = re.sub(r'await ctx\.send\(', 'await interaction.response.send_message(', content)

# Sauvegarder
with open(r'u:\Projets\Git\ba-tbot-v2\bot\cogs\music.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Conversion terminée!")
