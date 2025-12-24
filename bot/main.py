"""Point d'entrée principal du bot Discord musical"""

import logging
import sys
import asyncio
from bot.bot import MusicBot
from bot.config import Config


def setup_logging():
    """Configure le système de logging"""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Format des logs
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # Configuration du logger racine
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log", encoding="utf-8")
        ]
    )
    
    # Réduire le niveau de log de discord.py pour éviter le spam
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)


async def main():
    """Fonction principale asynchrone"""
    # Configuration du logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("Démarrage du Bot Discord Musical")
    logger.info("=" * 50)
    
    # Vérifier la configuration
    try:
        Config.validate()
        logger.info("Configuration validée avec succès")
        
        if Config.has_spotify():
            logger.info("Intégration Spotify activée")
        else:
            logger.info("Intégration Spotify désactivée (credentials manquants)")
            
    except ValueError as e:
        logger.error(f"Erreur de configuration: {e}")
        sys.exit(1)
    
    # Créer et lancer le bot
    bot = MusicBot()
    
    try:
        async with bot:
            await bot.start(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Interruption par l'utilisateur (Ctrl+C)")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Bot arrêté")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
