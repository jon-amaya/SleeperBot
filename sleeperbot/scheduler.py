from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from sleeperbot.bot import bot
from sleeperbot.config import load_config

# GameDayBot's schedule, matched message for message. ET entries are fixed
# Eastern because they track kickoff windows; everything else follows the
# league's own TIMEZONE.
#
# (function, day_of_week, hour, minute, eastern)
JOBS = [
    ("get_waiver_report", "*", 7, 30, False),
    ("get_trades", "*", 7, 31, False),
    ("get_final", "tue", 7, 30, False),
    ("get_fortune_index", "tue", 8, 30, False),
    ("get_trophy_case", "tue", 9, 0, False),
    ("get_power_rankings", "tue", 18, 30, False),
    ("get_standings", "wed", 7, 30, False),
    ("get_win_matrix", "wed", 7, 31, False),
    ("get_matchups", "thu", 19, 30, True),
    ("get_scoreboard", "fri,mon", 7, 30, False),
    ("get_monitor", "sun", 7, 30, False),
    ("get_scoreboard", "sun", 16, 0, True),
    ("get_scoreboard", "sun", 20, 0, True),
    ("get_close_scores", "mon", 18, 30, True),
]

GAME_TIMEZONE = "America/New_York"


def _add_jobs(sched, config):
    start_date = config["start_date"]
    end_date = config["end_date"]

    for index, (function, days, hour, minute, eastern) in enumerate(JOBS):
        sched.add_job(
            bot,
            "cron",
            [function],
            id=f"{function}_{index}",
            day_of_week=days,
            hour=hour,
            minute=minute,
            start_date=start_date,
            end_date=end_date,
            timezone=GAME_TIMEZONE if eastern else config["timezone"],
            replace_existing=True,
        )


def run():
    """Blocking scheduler: webhook-only mode, no Discord bot/gateway involved."""
    config = load_config()
    sched = BlockingScheduler(job_defaults={"misfire_grace_time": 15 * 60})
    _add_jobs(sched, config)
    print("Ready!")
    sched.start()


def start_background(config):
    """
    Non-blocking scheduler: used when a Discord bot (gateway) is also running
    in this process, since discord.py's Client.run() needs to own the main
    thread. Scheduled jobs still just call the existing synchronous, requests-
    based bot() function -- unaffected by the bot's asyncio event loop.
    """
    sched = BackgroundScheduler(job_defaults={"misfire_grace_time": 15 * 60})
    _add_jobs(sched, config)
    sched.start()
    return sched
