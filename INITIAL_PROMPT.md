# Concept
Je veux faire un bot discord utilisant l'api python discord.py
Le bot doit pouvoir :
- Récupérer un stream de musique depuis une playlist ou une vidéo youtube et spotify
- Permettre de diffuser de la musique dans un canal vocal
- Pouvoir jouer du son depuis une playlist
- Pouvoir être utilisé sur plusieurs serveurs simultanément
- Recevoir des commandes (qui seront listées plus bas)
- Envoyer des messages dans un channel
- Enregistrer des playlists

# Commandes
- play <playlist_id/url>/<song name>/<song url>
- stop
- pause
- resume
- skip
- queue
- nowplaying
- volume
- save_playlist <name>
- load_playlist <name>
- remove_playlist <name>
- list_playlists


# Technique
- Utiliser l'api discord.py
- Utiliser une base de données json ou sqlite