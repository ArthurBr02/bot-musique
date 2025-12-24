"""Script pour convertir les commandes playlist en slash commands"""
import re

# Lire le fichier
with open(r'u:\Projets\Git\ba-tbot-v2\bot\cogs\playlist.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remplacements de décorateurs
replacements = [
    (r"@commands\.command\(name='save_playlist', aliases=\['savepl'\]\)", '@app_commands.command(name="save_playlist", description="Sauvegarde la queue actuelle")\n    @app_commands.describe(name="Nom de la playlist")'),
    (r"@commands\.command\(name='load_playlist', aliases=\['loadpl'\]\)", '@app_commands.command(name="load_playlist", description="Charge une playlist")\n    @app_commands.describe(name="Nom de la playlist")'),
    (r"@commands\.command\(name='list_playlists', aliases=\['playlists', 'pls'\]\)", '@app_commands.command(name="list_playlists", description="Liste toutes les playlists")'),
    (r"@commands\.command\(name='remove_playlist', aliases=\['deletepl', 'delpl'\]\)", '@app_commands.command(name="remove_playlist", description="Supprime une playlist")\n    @app_commands.describe(name="Nom de la playlist")'),
    (r"@commands\.command\(name='playlist_info', aliases=\['plinfo'\]\)", '@app_commands.command(name="playlist_info", description="Affiche les détails d\'une playlist")\n    @app_commands.describe(name="Nom de la playlist")'),
    (r"@commands\.command\(name='save_spotify_playlist', aliases=\['savesp', 'importsp'\]\)", '@app_commands.command(name="save_spotify_playlist", description="Importe une playlist Spotify")\n    @app_commands.describe(url="URL Spotify (playlist ou album)", name="Nom de la playlist")'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Remplacer les signatures de fonctions
content = re.sub(r'async def (save_playlist|load_playlist|list_playlists|remove_playlist|playlist_info|save_spotify_playlist)\(self, ctx: commands\.Context', r'async def \1(self, interaction: discord.Interaction', content)

# Remplacer ctx par interaction dans le corps des fonctions
content = re.sub(r'\bctx\.send\(', 'interaction.response.send_message(', content)
content = re.sub(r'\bctx\.author', 'interaction.user', content)
content = re.sub(r'\bctx\.guild', 'interaction.guild', content)
content = re.sub(r'self\._get_player\(ctx\)', 'self._get_player(interaction)', content)

# Cas spéciaux pour les messages avec edit (load_playlist et save_spotify_playlist)
content = re.sub(r'loading_msg = await interaction\.response\.send_message\(', 'await interaction.response.defer()\n        loading_msg = await interaction.followup.send(', content)
content = re.sub(r'await loading_msg\.edit\(', 'await loading_msg.edit(', content)

# Sauvegarder
with open(r'u:\Projets\Git\ba-tbot-v2\bot\cogs\playlist.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Conversion des commandes playlist terminée!")
