import logging

from sleeperbot import formatting
from sleeperbot.config import load_config
from sleeperbot import charts
from sleeperbot.discord_client import (
    attach_image,
    build_embeds,
    send_embeds,
    send_message,
)
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
        get_trophies, get_power_rankings, get_waiver_report, get_monitor,
        get_trades, get_fortune_index, get_win_matrix, get_trophy_case,
        get_final, init.
    config : dict, optional
        Pre-loaded config (mainly for tests); defaults to load_config().
    league : SleeperLeague, optional
        Pre-built league (mainly for tests); defaults to a fresh SleeperLeague.
    """
    config = config or load_config()
    league = league or SleeperLeague(SleeperClient(config["league_id"]))

    logger.info("Function: %s", function)

    # Each entry renders as its own embed, so a report that pairs two different
    # kinds of content (get_final: a table plus prose trophies) keeps each in
    # the presentation that suits it.
    reports = []

    if function == "get_standings":
        reports = [("get_standings", formatting.build_standings(league))]
    elif function == "get_matchups":
        reports = [("get_matchups", formatting.build_matchups(league))]
    elif function == "get_scoreboard":
        reports = [("get_scoreboard", formatting.build_scoreboard(league))]
    elif function == "get_close_scores":
        reports = [(
            "get_close_scores",
            formatting.build_close_scores(league, threshold=config["close_scores_threshold"]),
        )]
    elif function == "get_trophies":
        reports = [("get_trophies", formatting.build_trophies(league))]
    elif function == "get_power_rankings":
        reports = [("get_power_rankings", formatting.build_power_rankings(league))]
    elif function == "get_waiver_report":
        reports = [("get_waiver_report", formatting.build_waiver_report(league))]
    elif function == "get_monitor":
        reports = [("get_monitor", formatting.build_monitor(league))]
    elif function == "get_trades":
        reports = [("get_trades", formatting.build_trades(league))]
    elif function == "get_fortune_index":
        reports = [("get_fortune_index", formatting.build_fortune_index(league))]
    elif function == "get_win_matrix":
        reports = [("get_win_matrix", formatting.build_win_matrix(league))]
    elif function == "get_trophy_case":
        reports = [("get_trophy_case", formatting.build_trophy_case(league))]
    elif function == "get_final":
        week = league.current_week - 1
        box_scores = league.box_scores(week)
        reports = [
            ("get_final", formatting.build_scoreboard(
                league, week=week, box_scores=box_scores, final=True)),
            ("get_trophies", formatting.build_trophies(
                league, week=week, box_scores=box_scores)),
        ]
    elif function == "init":
        message = config.get("init_msg", "")
        if message:
            send_message(config["webhook_url"], message)
        return
    else:
        logger.warning("Unknown function: %s", function)
        return

    embeds = []
    footer = f"{league.name} • {league.season}"
    for key, text in reports:
        if not formatting.has_sendable_content(text):
            continue
        title, color, monospace = formatting.REPORT_STYLE.get(key, formatting.DEFAULT_STYLE)
        embeds += build_embeds(
            title, formatting.strip_header(text), color, monospace, footer=footer
        )

    if not embeds:
        return

    files = []
    chart = _chart_for(function, league)
    if chart:
        name, png = chart
        attached = attach_image(embeds, name, png)
        if attached:
            files.append(attached)

    send_embeds(config["webhook_url"], embeds, files=files or None)


def _chart_for(function, league):
    """The trend image that rides along with a report, if it has one."""
    try:
        names = formatting.team_names(league)
        if function == "get_final":
            png = charts.weekly_scores_chart(formatting.season_score_series(league), names)
            return ("weekly_scores.png", png) if png else None
        if function == "get_power_rankings":
            png = charts.rank_trend_chart(
                formatting.power_rank_series(league), names, "Power rankings by week"
            )
            return ("power_rankings_trend.png", png) if png else None
        if function == "get_standings":
            png = charts.rank_trend_chart(
                formatting.standings_rank_series(league), names, "Standings by week"
            )
            return ("standings_trend.png", png) if png else None
        if function == "get_fortune_index":
            png = charts.bad_management_chart(formatting.bench_point_totals(league), names)
            return ("bad_management.png", png) if png else None
    except Exception:
        # A chart is a garnish. If it fails to render, the report it decorates
        # should still go out.
        logger.exception("Chart rendering failed for %s", function)
    return None
