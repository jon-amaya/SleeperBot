from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from sleeperbot.bot import bot
from sleeperbot.config import load_config

# close scores:    monday evening at 6:30pm east coast time.
# power rankings:  tuesday evening at 6:30pm local time.
# final scores:    tuesday morning at 7:30am local time.
# standings:       wednesday morning at 7:30am local time.
# waiver report:   wednesday morning at 7:31am local time (or daily).
# matchups:        thursday evening at 7:30pm east coast time.
# scoreboard:      friday and monday mornings, and sunday afternoon/evening.


def _add_jobs(sched, config):
    game_tz = "America/New_York"
    my_tz = config["timezone"]
    start_date = config["start_date"]
    end_date = config["end_date"]

    sched.add_job(
        bot, "cron", ["get_close_scores"], id="close_scores",
        day_of_week="mon", hour=18, minute=30,
        start_date=start_date, end_date=end_date, timezone=game_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_power_rankings"], id="power_rankings",
        day_of_week="tue", hour=18, minute=30,
        start_date=start_date, end_date=end_date, timezone=my_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_final"], id="final",
        day_of_week="tue", hour=7, minute=30,
        start_date=start_date, end_date=end_date, timezone=my_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_standings"], id="standings",
        day_of_week="wed", hour=7, minute=30,
        start_date=start_date, end_date=end_date, timezone=my_tz, replace_existing=True,
    )
    waiver_days = "*" if config["daily_waiver"] else "wed"
    sched.add_job(
        bot, "cron", ["get_waiver_report"], id="waiver_report",
        day_of_week=waiver_days, hour=7, minute=31,
        start_date=start_date, end_date=end_date, timezone=my_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_matchups"], id="matchups",
        day_of_week="thu", hour=19, minute=30,
        start_date=start_date, end_date=end_date, timezone=game_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_scoreboard"], id="scoreboard1",
        day_of_week="fri,mon", hour=7, minute=30,
        start_date=start_date, end_date=end_date, timezone=my_tz, replace_existing=True,
    )
    sched.add_job(
        bot, "cron", ["get_scoreboard"], id="scoreboard2",
        day_of_week="sun", hour="16,20",
        start_date=start_date, end_date=end_date, timezone=game_tz, replace_existing=True,
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
