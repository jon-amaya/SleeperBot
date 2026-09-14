"""
Report builders, following the message formats used by
dtcarls/fantasy_football_chat_bot (the bot GameDayBot grew out of): a header
line followed by rows, joined with newlines, as plain text.

Three of its reports have no Sleeper equivalent and are deliberately absent:
projected scoreboards and the over/under-achiever trophies both need player
projections, and power rankings carry no playoff percentage. Sleeper's free
API publishes none of those.
"""

from datetime import date, datetime, timezone

from sleeperbot import power_rankings as pr

# Returned when a week has nothing to report, in place of a bare header with no
# rows under it. bot.py drops these rather than posting them.
NO_MATCHUP_DATA = "No matchup data available."
NO_TROPHY_DATA = "No matchup data available for trophies."

_NO_DATA_SENTINELS = frozenset({NO_MATCHUP_DATA, NO_TROPHY_DATA})

FLEX_ELIGIBILITY = {
    "FLEX": {"RB", "WR", "TE"},
    "WRRB_FLEX": {"RB", "WR"},
    "REC_FLEX": {"WR", "TE"},
    "SUPER_FLEX": {"QB", "RB", "WR", "TE"},
    "IDP_FLEX": {"DL", "LB", "DB"},
}
BENCH_SLOTS = {"BN", "IR", "TAXI"}


# Per-report presentation: embed title, colour, and whether the body sits in a
# code block. Tabular reports must: a code fence is the only place column
# padding survives, since Discord renders ordinary message text in a
# proportional font. Prose reports stay outside one so their emoji keep their
# colour and markdown still renders.
REPORT_STYLE = {
    "get_scoreboard": ("🏈 Score Update", 0x3498DB, True),
    "get_final": ("🏁 Final Score Update", 0x3498DB, True),
    "get_standings": ("📊 Current Standings", 0xF1C40F, True),
    "get_matchups": ("📅 Matchups", 0x2ECC71, True),
    "get_close_scores": ("⚡ Close Scores", 0x3498DB, True),
    "get_power_rankings": ("💪 Power Rankings", 0x9B59B6, True),
    "get_fortune_index": ("🎲 Fortune Index", 0x9B59B6, True),
    "get_win_matrix": ("🔢 Win Matrix", 0xF1C40F, True),
    "get_trophy_case": ("👑 Trophy Case", 0xE67E22, True),
    "get_trophies": ("🏆 Trophies of the Week", 0xE67E22, False),
    "get_waiver_report": ("💰 Waiver Report", 0x1ABC9C, False),
    "get_monitor": ("🚑 Players to Monitor", 0xE74C3C, False),
    "get_trades": ("🚨 Trade Announcement", 0xE91E63, False),
}
DEFAULT_STYLE = ("SleeperBot", 0x99AAB5, False)

# Win Matrix and Trophy Case only say anything once there is a season to
# summarise, so both hold until this many weeks are complete.
MIN_WEEKS_FOR_SEASON_REPORTS = 2


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


def _name_width(names, cap=22):
    """Width of the team-name column: the longest name present, within reason."""
    return min(max((len(n) for n in names), default=0), cap)


def _align_records(records):
    """Pad W-L records so wins right-align and losses left-align in a column."""
    parts = [r.split("-", 1) for r in records]
    wins_w = max((len(w) for w, _ in parts), default=0)
    rest_w = max((len(r) for _, r in parts), default=0)
    return [f"{w:>{wins_w}}-{r:<{rest_w}}" for w, r in parts]


def abbreviations(teams):
    """
    Four-letter tags for the score tables, where two full names per line would
    run too wide to read. Sleeper has no abbreviation field (ESPN does, which
    is where GameDayBot's DYNK and PUNT come from), so these are derived:
    leading alphanumerics of the name, widened and then numbered on collision
    so no two teams ever share a tag.
    """
    tags = {}
    used = set()
    for team in teams:
        letters = "".join(c for c in team.name if c.isalnum()).upper() or "TEAM"
        tag = letters[:4]
        if tag in used:
            for width in range(5, len(letters) + 1):
                if letters[:width] not in used:
                    tag = letters[:width]
                    break
            else:
                suffix = 2
                while f"{letters[:3]}{suffix}" in used:
                    suffix += 1
                tag = f"{letters[:3]}{suffix}"
        used.add(tag)
        tags[team.roster_id] = tag
    width = max((len(t) for t in tags.values()), default=4)
    return {rid: tag.ljust(width) for rid, tag in tags.items()}


def _tags_for(league, games):
    """Abbreviations covering every team in these games, league roster first so
    a team's tag stays the same from one report to the next."""
    seen = {}
    for team in list(league.teams()) + [t for m in games for t in (m.home, m.away)]:
        if team and team.roster_id not in seen:
            seen[team.roster_id] = team
    return abbreviations(seen.values())


def build_scoreboard(league, week=None, box_scores=None, final=False):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    if not games:
        return NO_MATCHUP_DATA

    tags = _tags_for(league, games)
    rows = [
        f"{tags[m.home.roster_id]} {m.home_score:6.2f} - {m.away_score:6.2f} {tags[m.away.roster_id]}"
        for m in games
    ]
    header = "Final Score Update" if final else "Score Update"
    return "\n".join([header, ""] + rows)


def build_standings(league):
    standings = league.standings()
    records = _align_records([f"{t.wins}-{t.losses}" for t in standings])
    rows = [
        f"{pos:2}: ({record}) {team.name}"
        for pos, (team, record) in enumerate(zip(standings, records), start=1)
    ]

    cutoff = league.playoff_teams
    if 0 < cutoff < len(rows):
        rows.insert(cutoff, "-" * 12 + " playoff line " + "-" * 12)

    return "\n".join(["Current Standings", ""] + rows)


def build_matchups(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    games = _played(box_scores)
    if not games:
        return NO_MATCHUP_DATA

    teams = [t for m in games for t in (m.home, m.away)]
    # Before anyone has played, every record is 0-0 -- a column of noise. They
    # appear only once they mean something.
    played_yet = any(team.wins or team.losses for team in teams)
    width = _name_width([t.name for t in teams])

    rows = [f"{_clip(m.home.name, width)} vs {m.away.name}" for m in games]
    if played_yet:
        records = _align_records([f"{t.wins}-{t.losses}" for t in teams])
        rows += [""]
        rows += [
            f"{_clip(m.home.name, width):<{width}} ({home}) vs ({away}) {m.away.name}"
            for m, home, away in zip(games, records[::2], records[1::2])
        ]

    return "\n".join(["Matchups", ""] + rows)


def build_close_scores(league, week=None, box_scores=None, threshold=15.0):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)

    games = _played(box_scores)
    tags = _tags_for(league, games)
    rows = []
    for m in games:
        if abs(m.home_score - m.away_score) <= threshold:
            rows.append(
                f"{tags[m.home.roster_id]} {m.home_score:6.2f} - "
                f"{m.away_score:6.2f} {tags[m.away.roster_id]}"
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
        "👑 High score 👑",
        f"{high_team.name} with {high_score:.2f} points",
        "",
        "💩 Low score 💩",
        f"{low_team.name} with {low_score:.2f} points",
    ]

    if blowout_winner:
        text += [
            "",
            "😱 Blow out 😱",
            f"{blowout_winner.name} blew out {blowout_loser.name} by {blowout_margin:.2f} points",
        ]
    if close_winner:
        text += [
            "",
            "😅 Close win 😅",
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
        "🍀 Lucky 🍀",
        f"{lucky.name} was {lucky_w}-{lucky_l} against the league, but still got the win",
        "",
        "😡 Unlucky 😡",
        f"{unlucky.name} was {unlucky_w}-{unlucky_l} against the league, but still took an L",
    ]


def _manager_scores(league, games):
    """(team, actual, optimal, percent) per team, best-managed lineup first."""
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
    scored.sort(key=lambda s: s[3], reverse=True)
    return scored


def _manager_trophies(league, games):
    scored = _manager_scores(league, games)
    if not scored:
        return []

    best_team, _, _, best_pct = scored[0]
    worst_team, worst_actual, worst_optimal, worst_pct = scored[-1]

    return [
        "",
        "🤖 Best Manager 🤖",
        f"{best_team.name} scored {best_pct:.2f}% of their optimal score!",
        "",
        "🤡 Worst Manager 🤡",
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
    rows = [
        f"{score:5.2f} - {team_by_roster[rid].name}"
        for rid, score in ranking
        if rid in team_by_roster
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


def season_weeks(league, through=None):
    """
    Completed weeks of this season, as {week: box_scores}. The league caches
    each fetch, so the reports that all walk the season share one set of calls.
    """
    last = through if through is not None else league.current_week - 1
    weeks = {}
    for week in range(1, max(last, 0) + 1):
        games = _played(league.box_scores(week))
        if games:
            weeks[week] = games
    return weeks


def _weekly_fortune(games):
    """
    Per team: how many opponents it outscored this week, against how many it
    actually needed to. Winning with a bottom-half score is luck; losing with a
    top-half one is not.
    """
    records = _all_play_records(games)
    fortune = {}
    for m in games:
        if m.home_score == m.away_score:
            continue
        winner = m.home if m.home_score > m.away_score else m.away
        loser = m.away if m.home_score > m.away_score else m.home
        for team, won in ((winner, True), (loser, False)):
            beat, lost_to = records[team.roster_id]
            total = beat + lost_to
            if not total:
                continue
            # Share of the league you beat, versus the result you got.
            expected = beat / total
            fortune[team.roster_id] = round(100 * ((1.0 if won else 0.0) - expected))
    return fortune


def build_fortune_index(league, week=None):
    week = week if week is not None else league.current_week - 1
    weeks = season_weeks(league, through=week)
    if not weeks:
        return NO_MATCHUP_DATA

    totals = {}
    for games in weeks.values():
        for roster_id, score in _weekly_fortune(games).items():
            totals[roster_id] = totals.get(roster_id, 0) + score

    team_by_roster = {t.roster_id: t for t in league.teams()}
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    if not ranked:
        return NO_MATCHUP_DATA

    width = _name_width([team_by_roster[r].name for r, _ in ranked if r in team_by_roster])
    rows = []
    for pos, (roster_id, score) in enumerate(ranked, start=1):
        team = team_by_roster.get(roster_id)
        if not team:
            continue
        if pos == 1:
            mark = "👑"
        elif pos == 2:
            mark = "🍀"
        elif pos == len(ranked):
            mark = "💀"
        elif pos == len(ranked) - 1:
            mark = "😡"
        else:
            mark = "  "
        rows.append(f"{pos:2}. {mark} {_clip(team.name, width):<{width}} - {score:+d}")

    return "\n".join([f"Fortune Index - Week {week}", ""] + rows)


def build_win_matrix(league):
    """Standings with the schedule taken out: everyone plays everyone, weekly."""
    weeks = season_weeks(league)
    if len(weeks) < MIN_WEEKS_FOR_SEASON_REPORTS:
        return ""

    tally = {}
    for games in weeks.values():
        for roster_id, (wins, losses) in _all_play_records(games).items():
            won, lost = tally.get(roster_id, (0, 0))
            tally[roster_id] = (won + wins, lost + losses)

    team_by_roster = {t.roster_id: t for t in league.teams()}
    ranked = sorted(
        tally.items(),
        key=lambda item: item[1][0] / max(item[1][0] + item[1][1], 1),
        reverse=True,
    )

    width = _name_width([team_by_roster[r].name for r, _ in ranked if r in team_by_roster])
    records = _align_records([f"{w}-{l}" for _, (w, l) in ranked])
    rows = [
        f"{pos:2}. {_clip(team_by_roster[rid].name, width):<{width}} ({record})"
        for pos, ((rid, _), record) in enumerate(zip(ranked, records), start=1)
        if rid in team_by_roster
    ]
    return "\n".join(["Standings if everyone played every team every week", ""] + rows)


# Trophy Case columns, in display order.
TROPHY_ICONS = ["👑", "💩", "😱", "😅", "🍀", "😡", "🤖", "🤡"]


def weekly_trophy_winners(league, games):
    """
    Which roster won each Trophy Case column this week, in TROPHY_ICONS order.
    Returns a list the same length, with None where nothing was awarded.
    """
    scores = [(m.home_score, m.home) for m in games] + [(m.away_score, m.away) for m in games]
    high = max(scores, key=lambda s: s[0])[1]
    low = min(scores, key=lambda s: s[0])[1]

    blowout = close = None
    best_margin, tight_margin = -1.0, None
    for m in games:
        margin = abs(m.home_score - m.away_score)
        if margin == 0:
            continue
        winner = m.home if m.home_score > m.away_score else m.away
        if margin > best_margin:
            best_margin, blowout = margin, winner
        if tight_margin is None or margin < tight_margin:
            tight_margin, close = margin, winner

    lucky = unlucky = None
    luck = _luck_trophies(games)
    if luck:
        lucky_name = luck[2].split(" was ")[0]
        unlucky_name = luck[5].split(" was ")[0]
        by_name = {t.name: t for _, t in scores}
        lucky, unlucky = by_name.get(lucky_name), by_name.get(unlucky_name)

    best_mgr = worst_mgr = None
    managers = _manager_scores(league, games)
    if managers:
        best_mgr = managers[0][0]
        worst_mgr = managers[-1][0]

    return [high, low, blowout, close, lucky, unlucky, best_mgr, worst_mgr]


def build_trophy_case(league):
    weeks = season_weeks(league)
    if len(weeks) < MIN_WEEKS_FOR_SEASON_REPORTS:
        return ""

    tally = {t.roster_id: [0] * len(TROPHY_ICONS) for t in league.teams()}
    for games in weeks.values():
        for column, team in enumerate(weekly_trophy_winners(league, games)):
            if team is not None and team.roster_id in tally:
                tally[team.roster_id][column] += 1

    team_by_roster = {t.roster_id: t for t in league.teams()}
    ranked = sorted(tally.items(), key=lambda item: sum(item[1]), reverse=True)
    width = _name_width([t.name for t in league.teams()])

    # An emoji occupies roughly two monospace cells, so each column is the
    # emoji plus two spaces; counts pad to the same four to stay under them.
    rows = [" " * (width + 2) + "  ".join(TROPHY_ICONS)]
    for roster_id, counts in ranked:
        team = team_by_roster.get(roster_id)
        if not team:
            continue
        cells = "".join(f"{(str(c) if c else '·'):<4}" for c in counts).rstrip()
        rows.append(f"{_clip(team.name, width):<{width}}  {cells}")

    legend = "👑 high  💩 low  😱 blowout  😅 close  🍀 lucky  😡 unlucky  🤖 best  🤡 worst"
    return "\n".join([f"Trophy Case - through week {max(weeks)}", ""] + rows + ["", legend])


def season_score_series(league):
    """{week: {roster_id: score}} for every completed week -- chart input."""
    series = {}
    for week, games in season_weeks(league).items():
        series[week] = {}
        for m in games:
            series[week][m.home.roster_id] = m.home_score
            series[week][m.away.roster_id] = m.away_score
    return series


def standings_rank_series(league):
    """{week: {roster_id: rank}} by cumulative record, week by week."""
    tally = {}
    series = {}
    for week, games in sorted(season_weeks(league).items()):
        for m in games:
            winner = m.home if m.home_score > m.away_score else m.away
            loser = m.away if m.home_score > m.away_score else m.home
            for team, won in ((winner, True), (loser, False)):
                wins, losses, points = tally.get(team.roster_id, (0, 0, 0.0))
                tally[team.roster_id] = (wins + int(won), losses + int(not won), points)
            tally[m.home.roster_id] = (
                tally[m.home.roster_id][0], tally[m.home.roster_id][1],
                tally[m.home.roster_id][2] + m.home_score,
            )
            tally[m.away.roster_id] = (
                tally[m.away.roster_id][0], tally[m.away.roster_id][1],
                tally[m.away.roster_id][2] + m.away_score,
            )
        order = sorted(tally.items(), key=lambda item: (-item[1][0], -item[1][2]))
        series[week] = {rid: pos for pos, (rid, _) in enumerate(order, start=1)}
    return series


def power_rank_series(league):
    """{week: {roster_id: rank}} from the power-ranking model, week by week."""
    weeks = season_weeks(league)
    series = {}
    running = {}
    for week in sorted(weeks):
        for m in weeks[week]:
            running.setdefault(m.home.roster_id, []).append(m.home_score)
            running.setdefault(m.away.roster_id, []).append(m.away_score)
        ranking = pr.compute_power_rankings({k: list(v) for k, v in running.items()})
        series[week] = {rid: pos for pos, (rid, _) in enumerate(ranking, start=1)}
    return series


def bench_point_totals(league):
    """{roster_id: points left on the bench across the season}."""
    totals = {}
    for games in season_weeks(league).values():
        for m in games:
            totals[m.home.roster_id] = totals.get(m.home.roster_id, 0.0) + m.home_bench_points
            totals[m.away.roster_id] = totals.get(m.away.roster_id, 0.0) + m.away_bench_points
    return totals


def team_names(league):
    return {t.roster_id: t.name for t in league.teams()}


def build_trades(league, week=None, today=None):
    """
    Completed trades, announced the way GameDayBot does: each side's haul
    listed under the team receiving it, players and draft picks together.
    """
    week = week or league.current_week
    today = today or date.today().strftime("%Y-%m-%d")
    team_by_roster = {t.roster_id: t for t in league.teams()}

    blocks = []
    for txn in league.raw_transactions(week):
        if txn.get("type") != "trade" or txn.get("status") != "complete":
            continue
        stamp = txn.get("status_updated")
        if stamp is None:
            continue
        if datetime.fromtimestamp(stamp / 1000, timezone.utc).strftime("%Y-%m-%d") != today:
            continue

        haul = {rid: [] for rid in txn.get("roster_ids") or []}
        for player_id, roster_id in (txn.get("adds") or {}).items():
            haul.setdefault(roster_id, []).append(
                f"{league.player_position(player_id)} {league.player_name(player_id)}"
            )
        for pick in txn.get("draft_picks") or []:
            haul.setdefault(pick.get("owner_id"), []).append(
                f"{pick.get('season')} round {pick.get('round')} pick"
            )
        for money in txn.get("waiver_budget") or []:
            haul.setdefault(money.get("receiver"), []).append(
                f"${money.get('amount')} FAAB"
            )

        lines = ["Status: EXECUTED"]
        for roster_id, items in haul.items():
            team = team_by_roster.get(roster_id)
            if not team or not items:
                continue
            lines.append(f"{team.name} receives:")
            lines += [f"  • {item}" for item in items]
        if len(lines) > 1:
            blocks.append("\n".join(lines))

    if not blocks:
        return ""
    return "🚨TRADE ANNOUNCEMENT🚨\n\n" + "\n\n".join(blocks)


def build_waiver_report(league, week=None, today=None):
    week = week or league.current_week
    today = today or date.today().strftime("%Y-%m-%d")

    blocks = []
    for item in league.transactions_for_week(week):
        if item.status_updated is None:
            continue
        txn_date = datetime.fromtimestamp(item.status_updated / 1000, timezone.utc).strftime("%Y-%m-%d")
        if txn_date != today:
            continue

        lines = [item.team_name]
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
