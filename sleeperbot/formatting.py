"""
Report builders, following the message formats used by
dtcarls/fantasy_football_chat_bot (the bot GameDayBot grew out of): a header
line followed by rows, joined with newlines, as plain text.

Three of its reports have no Sleeper equivalent and are deliberately absent:
projected scoreboards and the over/under-achiever trophies both need player
projections, and power rankings carry no playoff percentage. Sleeper's free
API publishes none of those.
"""

from datetime import date, datetime

from sleeperbot import power_rankings as pr

# Returned when a week has nothing to report, in place of a bare header with no
# rows under it. bot.py drops these rather than posting them.
NO_MATCHUP_DATA = "No matchup data available."
NO_TROPHY_DATA = "No matchup data available for trophies."

_NO_DATA_SENTINELS = frozenset({NO_MATCHUP_DATA, NO_TROPHY_DATA})

# Sleeper has no team-abbreviation field, so reports lead with team names and
# pad them to a common column instead. The column is sized to the longest name
# actually in the league rather than a fixed width, so nothing is truncated
# unless someone picks a genuinely absurd name -- past MAX_NAME_WIDTH the line
# gets wide enough to wrap on a phone, which is worse than clipping one team.
MAX_NAME_WIDTH = 24
BAR_WIDTH = 12
_EIGHTHS = "▏▎▍▌▋▊▉█"

FLEX_ELIGIBILITY = {
    "FLEX": {"RB", "WR", "TE"},
    "WRRB_FLEX": {"RB", "WR"},
    "REC_FLEX": {"WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
    "IDP_FLEX": {"DL", "LB", "DB"},
}
BENCH_SLOTS = {"BN", "IR", "TAXI"}


# Per-report presentation: emoji title, embed colour, and whether the body is a
# table. Column padding only survives in a code block -- Discord renders normal
# message text in a proportional font, where the padding collapses -- so every
# tabular report sets monospace. Prose-style reports read better without it.
REPORT_STYLE = {
    "get_scoreboard": ("🏈 Score Update", 0x3498DB, True),
    "get_final": ("🏁 Final Score", 0x3498DB, True),
    "get_standings": ("📊 Current Standings", 0xF1C40F, True),
    "get_matchups": ("📅 Matchups", 0x2ECC71, True),
    "get_close_scores": ("⚡ Close Scores", 0x3498DB, True),
    "get_power_rankings": ("💪 Power Rankings", 0x9B59B6, True),
    "get_trophies": ("🏆 Trophies of the Week", 0xE67E22, False),
    "get_waiver_report": ("💰 Waiver Report", 0x1ABC9C, False),
    "get_monitor": ("🚑 Players to Monitor", 0xE74C3C, False),
}
DEFAULT_STYLE = ("SleeperBot", 0x99AAB5, False)


def has_sendable_content(message):
    if not message or not message.strip():
        return False
    return message.strip() not in _NO_DATA_SENTINELS


def strip_header(text):
    """
    Drop a report's own header line, which becomes the embed title instead of
    sitting inside the body.
    """
    body = text.split("\n", 1)[1] if "\n" in text else ""
    return body.strip("\n")


def _played(box_scores):
    return [m for m in box_scores if not m.is_bye]


def _clip(name, width):
    return name if len(name) <= width else name[: width - 1] + "…"


def _name_width(names):
    """Width of the team-name column: the longest name present, within reason."""
    return min(max((len(n) for n in names), default=0), MAX_NAME_WIDTH)


def _bar(value, peak, width=BAR_WIDTH):
    if peak <= 0:
        return ""
    filled = (value / peak) * width
    full = int(filled)
    out = "█" * full
    remainder = filled - full
    if remainder >= 0.0625 and full < width:
        out += _EIGHTHS[min(int(remainder * 8), 7)]
    return out


def _align_records(records):
    """Pad W-L records so wins right-align and losses left-align in a column."""
    parts = [r.split("-", 1) for r in records]
    wins_w = max((len(w) for w, _ in parts), default=0)
    rest_w = max((len(r) for _, r in parts), default=0)
    return [f"{w:>{wins_w}}-{r:<{rest_w}}" for w, r in parts]


def build_scoreboard(league, week=None, box_scores=None, final=False):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    if not games:
        return NO_MATCHUP_DATA

    peak = max(max(m.home_score, m.away_score) for m in games)
    width = _name_width([t.name for m in games for t in (m.home, m.away)])

    blocks = []
    for m in games:
        if m.home_score >= m.away_score:
            win, lose, ws, ls = m.home, m.away, m.home_score, m.away_score
        else:
            win, lose, ws, ls = m.away, m.home, m.away_score, m.home_score
        blocks.append(
            f"{_clip(win.name, width):<{width}} {ws:>7.2f} {_bar(ws, peak):<{BAR_WIDTH + 1}}\n"
            f"{_clip(lose.name, width):<{width}} {ls:>7.2f} {_bar(ls, peak):<{BAR_WIDTH + 1}}{ls - ws:>7.2f}"
        )

    header = "Final Score Update" if final else "Score Update"
    return "\n".join([header, ""] + ["\n\n".join(blocks)])


def build_standings(league):
    standings = league.standings()
    records = _align_records([f"{t.wins}-{t.losses}" for t in standings])
    rows = [
        f"{pos:2}: ({record}) {team.name}"
        for pos, (team, record) in enumerate(zip(standings, records), start=1)
    ]

    cutoff = league.playoff_teams
    if 0 < cutoff < len(rows):
        rows.insert(cutoff, "-" * 28 + " playoff line")

    return "\n".join(["Current Standings", ""] + rows)


def build_matchups(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    if not games:
        return NO_MATCHUP_DATA

    # One team per line, each next to its own record, seeded by current
    # standings position -- a single line pairing both teams runs wide enough
    # to scroll sideways on a phone, and puts the away record before the away
    # team it belongs to.
    seed = {team.roster_id: pos for pos, team in enumerate(league.standings(), start=1)}
    teams = [t for m in games for t in (m.home, m.away)]
    width = _name_width([t.name for t in teams])
    records = dict(
        zip(
            (t.roster_id for t in teams),
            _align_records([f"{t.wins}-{t.losses}" for t in teams]),
        )
    )

    # Before anyone has played, every record is 0-0 and the standings order is
    # arbitrary. Printing both columns would imply a pecking order that does
    # not exist yet, so week one lists names only.
    played_yet = any(team.wins or team.losses for team in teams)

    blocks = []
    for m in games:
        lines = []
        for team in (m.home, m.away):
            if played_yet:
                lines.append(
                    f"{seed.get(team.roster_id, 0):2}  "
                    f"{_clip(team.name, width):<{width}}  {records[team.roster_id]}"
                )
            else:
                lines.append(_clip(team.name, width))
        blocks.append("\n".join(lines))

    return "\n".join(["Matchups", ""] + ["\n\n".join(blocks)])


def build_close_scores(league, week=None, box_scores=None, threshold=15.0):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    width = _name_width([m.home.name for m in games])

    rows = []
    for m in games:
        margin = abs(m.home_score - m.away_score)
        if margin <= threshold:
            rows.append(
                f"{_clip(m.home.name, width):<{width}} {m.home_score:>7.2f} - "
                f"{m.away_score:>7.2f} {m.away.name}"
            )
    if not rows:
        return ""
    return "\n".join(["Close Scores", ""] + rows)


def _optimal_lineup_points(league, entry):
    """
    Best score the roster could have produced, filling dedicated slots before
    flex ones so a flex-eligible star isn't spent on a slot only he can fill.
    """
    slots = [s for s in league.roster_positions if s not in BENCH_SLOTS]
    if not slots:
        return 0.0

    pool = sorted(
        (
            (points or 0.0, pid, league.player_positions(pid))
            for pid, points in (entry.get("players_points") or {}).items()
        ),
        reverse=True,
        key=lambda item: item[0],
    )

    def eligible(slot, positions):
        if slot in FLEX_ELIGIBILITY:
            return bool(positions & FLEX_ELIGIBILITY[slot])
        return slot in positions

    ordered = [s for s in slots if s not in FLEX_ELIGIBILITY]
    ordered += [s for s in slots if s in FLEX_ELIGIBILITY]

    used, total = set(), 0.0
    for slot in ordered:
        for points, pid, positions in pool:
            if pid in used or not eligible(slot, positions):
                continue
            used.add(pid)
            total += points
            break
    return total


def _all_play_records(box_scores):
    """Each team's record against the entire league for the week."""
    games = _played(box_scores)
    scores = [(m.home_score, m.home) for m in games] + [(m.away_score, m.away) for m in games]
    records = {}
    for score, team in scores:
        wins = sum(1 for other, _ in scores if score > other)
        losses = sum(1 for other, _ in scores if score < other)
        records[team.roster_id] = (wins, losses)
    return records


def build_trophies(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    if not games:
        return NO_TROPHY_DATA

    scores = [(m.home_score, m.home) for m in games] + [(m.away_score, m.away) for m in games]
    high_score, high_team = max(scores, key=lambda s: s[0])
    low_score, low_team = min(scores, key=lambda s: s[0])

    blowout_margin, blowout_winner, blowout_loser = -1.0, None, None
    close_margin, close_winner, close_loser = None, None, None
    for m in games:
        margin = abs(m.home_score - m.away_score)
        if margin == 0:
            continue
        winner, loser = (m.home, m.away) if m.home_score > m.away_score else (m.away, m.home)
        if margin > blowout_margin:
            blowout_margin, blowout_winner, blowout_loser = margin, winner, loser
        if close_margin is None or margin < close_margin:
            close_margin, close_winner, close_loser = margin, winner, loser

    text = [
        "Trophies of the week:",
        "",
        "**👑 High score 👑**",
        f"{high_team.name} with {high_score:.2f} points",
        "",
        "**💩 Low score 💩**",
        f"{low_team.name} with {low_score:.2f} points",
    ]

    if blowout_winner:
        text += [
            "",
            "**😱 Blow out 😱**",
            f"{blowout_winner.name} blew out {blowout_loser.name} by {blowout_margin:.2f} points",
        ]
    if close_winner:
        text += [
            "",
            "**😅 Close win 😅**",
            f"{close_winner.name} barely beat {close_loser.name} by {close_margin:.2f} points",
        ]

    text += _luck_trophies(games)
    text += _manager_trophies(league, games)
    return "\n".join(text)


def _luck_trophies(games):
    """
    Lucky: the lowest scorer who still won. Unlucky: the highest scorer who
    still lost. Both compare against the whole league, not just the opponent.
    """
    records = _all_play_records(games)
    results = []
    for m in games:
        if m.home_score == m.away_score:
            continue
        winner, loser = (m.home, m.away) if m.home_score > m.away_score else (m.away, m.home)
        win_score = max(m.home_score, m.away_score)
        lose_score = min(m.home_score, m.away_score)
        results.append((win_score, winner, "W"))
        results.append((lose_score, loser, "L"))

    winners = [r for r in results if r[2] == "W"]
    losers = [r for r in results if r[2] == "L"]
    if not winners or not losers:
        return []

    _, lucky, _ = min(winners, key=lambda r: r[0])
    _, unlucky, _ = max(losers, key=lambda r: r[0])

    lucky_w, lucky_l = records[lucky.roster_id]
    unlucky_w, unlucky_l = records[unlucky.roster_id]

    return [
        "",
        "**🍀 Lucky 🍀**",
        f"{lucky.name} was {lucky_w}-{lucky_l} against the league, but still got the win",
        "",
        "**😡 Unlucky 😡**",
        f"{unlucky.name} was {unlucky_w}-{unlucky_l} against the league, but still took an L",
    ]


def _manager_trophies(league, games):
    scored = []
    for m in games:
        for team, entry, actual in (
            (m.home, m.home_entry, m.home_score),
            (m.away, m.away_entry, m.away_score),
        ):
            if not entry:
                continue
            optimal = _optimal_lineup_points(league, entry)
            if optimal <= 0:
                continue
            scored.append((team, actual, optimal, 100.0 * actual / optimal))

    if not scored:
        return []

    scored.sort(key=lambda s: s[3], reverse=True)
    best_team, _, _, best_pct = scored[0]
    worst_team, worst_actual, worst_optimal, worst_pct = scored[-1]

    return [
        "",
        "**🤖 Best Manager 🤖**",
        f"{best_team.name} scored {best_pct:.2f}% of their optimal score!",
        "",
        "**🤡 Worst Manager 🤡**",
        f"{worst_team.name} left {worst_optimal - worst_actual:.2f} points on their bench. "
        f"Only scoring {worst_pct:.2f}% of their optimal score.",
    ]


def build_power_rankings(league, week=None):
    week = week or max(league.current_week - 1, 1)
    weekly_scores = {}
    for w in range(1, week + 1):
        for m in _played(league.box_scores(w)):
            weekly_scores.setdefault(m.home.roster_id, []).append(m.home_score)
            weekly_scores.setdefault(m.away.roster_id, []).append(m.away_score)

    ranking = pr.compute_power_rankings(weekly_scores)
    if not ranking:
        return NO_MATCHUP_DATA

    team_by_roster = {t.roster_id: t for t in league.teams()}
    peak = max(score for _, score in ranking) or 1.0
    ranked = [(pos, team_by_roster[rid], score)
              for pos, (rid, score) in enumerate(ranking, start=1)
              if rid in team_by_roster]
    width = _name_width([team.name for _, team, _ in ranked])

    rows = [
        f"{pos:2}. {_clip(team.name, width):<{width}} "
        f"{_bar(score, peak):<{BAR_WIDTH + 1}} {score:5.1f}"
        for pos, team, score in ranked
    ]
    return "\n".join(["Power Rankings", ""] + rows)


def build_monitor(league, week=None, box_scores=None):
    """
    Starters carrying an injury designation, the week's lineup-check report.
    Sleeper's player feed supplies the status, so this needs no paid data.
    """
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    severity = {"Out": 0, "IR": 1, "PUP": 2, "Doubtful": 3, "Questionable": 4, "Sus": 5}

    blocks = []
    for m in box_scores:
        for team, entry in ((m.home, m.home_entry), (m.away, m.away_entry)):
            if not team or not entry:
                continue
            flagged = []
            for pid in entry.get("starters") or []:
                if not pid or pid == "0":
                    continue
                status = league.player_injury(pid)
                if not status:
                    continue
                flagged.append(
                    (
                        severity.get(status, 9),
                        f"{league.player_position(pid)} {league.player_name(pid)} - {status}",
                    )
                )
            if flagged:
                flagged.sort()
                blocks.append(f"**{team.name}**\n" + "\n".join(line for _, line in flagged))

    if not blocks:
        return "No Players to Monitor this week. Good Luck!"
    return "Starting Players to Monitor\n\n" + "\n\n".join(blocks)


def build_waiver_report(league, week=None, today=None):
    week = week or league.current_week
    today = today or date.today().strftime("%Y-%m-%d")

    blocks = []
    for item in league.transactions_for_week(week):
        if item.status_updated is None:
            continue
        txn_date = datetime.utcfromtimestamp(item.status_updated / 1000).strftime("%Y-%m-%d")
        if txn_date != today:
            continue

        lines = [f"**{item.team_name}**"]
        for add in item.adds:
            suffix = f" (${item.faab})" if item.faab is not None else ""
            lines.append(f"ADDED {add}{suffix}")
        for drop in item.drops:
            lines.append(f"DROPPED {drop}")
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    if not blocks:
        return ""
    return "\n\n".join([f"Waiver Report {today}:"] + blocks)
