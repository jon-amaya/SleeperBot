import logging

from sleeperbot.bot import bot
from sleeperbot.scheduler import run

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    bot("init")
    run()
