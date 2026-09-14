import logging

from sleeperbot.bot import bot
from sleeperbot.config import load_config

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    config = load_config()
    bot("init", config=config)

    if config.get("bot_token"):
        from sleeperbot.discord_bot import run as run_discord_bot
        from sleeperbot.scheduler import start_background

        start_background(config)
        run_discord_bot(config)  # blocking: owns the main thread for the gateway connection
    else:
        from sleeperbot.scheduler import run as run_scheduler

        run_scheduler()
