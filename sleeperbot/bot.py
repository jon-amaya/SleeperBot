import logging

from sleeperbot import formatting
from sleeperbot.config import load_config
from sleeperbot.discord_client import send_message
from sleeperbot.league import SleeperLeague
from sleeperbot.sleeper_client import SleeperClient

logger = logging.getLogger(__name__)


def bot(function, config=None, league=None):
    """
    Build the message for `function` and send it to Discord.

    Parameters
    ----------
    function : str
        One of: get_standings, get_matchups, get_scoreboard, get_close_scores,
        get_trophies, get_power_rankings, get_waiver_report, get_final, init.
    config : dict, optional
        Pre-loaded config (mainly for tests); defaults to load_config().
    league : SleeperLeague, optional
        Pre-built league (mainly for tests); defaults to a fresh SleeperLeague.
    """
    config = config or load_config()
    league = league or SleeperLeague(SleeperClient(config["league_id"]))

    logger.info("Function: %s", function)

    if function == "get_standings":
        text = formatting.build_standings(league)
    elif function == "get_matchups":
        text = formatting.build_matchups(league)
    elif function == "get_scoreboard":
        text = formatting.build_scoreboard(league)
    elif function == "get_close_scores":
        text = formatting.build_close_scores(league, threshold=config["close_scores_threshold"])
    elif function == "get_trophies":
        text = formatting.build_trophies(league)
    elif function == "get_power_rankings":
        text = formatting.build_power_rankings(league)
    elif function == "get_waiver_report":
        text = formatting.build_waiver_report(league)
    elif function == "get_final":
        week = league.current_week - 1
        box_scores = league.box_scores(week)
        scores = formatting.build_scoreboard(league, week=week, box_scores=box_scores)
        if scores == formatting.NO_MATCHUP_DATA:
            text = scores
        else:
            trophies = formatting.build_trophies(league, week=week, box_scores=box_scores)
            text = f"Final {scores}\n\n{trophies}"
    elif function == "init":
        text = config.get("init_msg", "")
    else:
        logger.warning("Unknown function: %s", function)
        return

    if text:
        send_message(config["webhook_url"], text)
