from datetime import date, datetime

from sleeperbot import power_rankings as pr

NO_MATCHUP_DATA = "No games this week"


def _played(box_scores):
    return [m for m in box_scores if not m.is_bye]


def build_standings(league):
    lines = ["Current Standings"]
    for pos, team in enumerate(league.standings(), start=1):
        lines.append(f"{pos:2}: ({team.record}) {team.name}")
    return "\n".join(lines)


def build_scoreboard(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    played = _played(box_scores)
    if not played:
        return NO_MATCHUP_DATA
    lines = [f"{m.home.name} {m.home_score:6.2f} - {m.away_score:6.2f} {m.away.name}" for m in played]
    return "\n".join(lines)


def build_matchups(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    played = _played(box_scores)
    if not played:
        return NO_MATCHUP_DATA
    lines = [f"{m.home.name} ({m.home.record}) vs ({m.away.record}) {m.away.name}" for m in played]
    return "\n".join(["Matchups"] + lines)


def build_close_scores(league, week=None, box_scores=None, threshold=15.0):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    lines = []
    for m in _played(box_scores):
        if abs(m.home_score - m.away_score) <= threshold:
            lines.append(f"{m.home.name} {m.home_score:6.2f} - {m.away_score:6.2f} {m.away.name}")
    if not lines:
        return "No close scores"
    return "\n".join(["Close Scores"] + lines)


def build_trophies(league, week=None, box_scores=None):
    box_scores = box_scores if box_scores is not None else league.box_scores(week)
    played = _played(box_scores)
    if not played:
        return NO_MATCHUP_DATA

    all_scores = [(m.home_score, m.home) for m in played] + [(m.away_score, m.away) for m in played]
    high_score, high_team = max(all_scores, key=lambda x: x[0])
    low_score, low_team = min(all_scores, key=lambda x: x[0])

    blowout_margin, blowout_team = -1.0, None
    close_margin, close_team = None, None
    for m in played:
        margin = abs(m.home_score - m.away_score)
        winner = m.home if m.home_score > m.away_score else m.away
        if margin > blowout_margin:
            blowout_margin, blowout_team = margin, winner
        if close_margin is None or margin < close_margin:
            close_margin, close_team = margin, winner

    lucky_team, unlucky_team = _lucky_and_unlucky(all_scores, played)

    bench_points = [(m.home_bench_points, m.home) for m in played] + [
        (m.away_bench_points, m.away) for m in played
    ]
    bench_leader_points, bench_leader_team = max(bench_points, key=lambda x: x[0])

    lines = ["Trophies"]
    lines.append(f"\U0001F451 Most Points: {high_team.name} ({high_score:.2f})")
    lines.append(f"\U0001F4A9 Least Points: {low_team.name} ({low_score:.2f})")
    if blowout_team:
        lines.append(f"\U0001F631 Blowout Win: {blowout_team.name} (by {blowout_margin:.2f})")
    if close_team:
        lines.append(f"\U0001F605 Close Win: {close_team.name} (by {close_margin:.2f})")
    if lucky_team:
        lines.append(f"\U0001F340 Lucky: {lucky_team.name}")
    if unlucky_team:
        lines.append(f"\U0001F621 Unlucky: {unlucky_team.name}")
    lines.append(f"\U0001F921 Most Points Left on Bench: {bench_leader_team.name} ({bench_leader_points:.2f})")

    return "\n".join(lines)


def _lucky_and_unlucky(all_scores, played):
    """
    All-play based: a team is "lucky" if it won its actual matchup despite a
    score that would have lost to at least half the league that week, and
    "unlucky" for the reverse. No projections needed -- purely who-beat-whom
    on the week's full score list.
    """
    n = len(all_scores)
    sorted_scores = sorted(score for score, _ in all_scores)

    def beat_count(score):
        return sum(1 for s in sorted_scores if s < score)

    lucky_team, lucky_gap = None, -1.0
    unlucky_team, unlucky_gap = None, -1.0

    for m in played:
        for team, score, won in (
            (m.home, m.home_score, m.home_score > m.away_score),
            (m.away, m.away_score, m.away_score > m.home_score),
        ):
            would_have_beaten = beat_count(score)
            expected_win = would_have_beaten >= n / 2
            if won and not expected_win:
                gap = n / 2 - would_have_beaten
                if gap > lucky_gap:
                    lucky_gap, lucky_team = gap, team
            elif not won and expected_win:
                gap = would_have_beaten - n / 2
                if gap > unlucky_gap:
                    unlucky_gap, unlucky_team = gap, team

    return lucky_team, unlucky_team


def build_power_rankings(league, week=None):
    week = week or max(league.current_week - 1, 1)
    weekly_scores = {}
    for w in range(1, week + 1):
        for m in _played(league.box_scores(w)):
            weekly_scores.setdefault(m.home.roster_id, []).append(m.home_score)
            weekly_scores.setdefault(m.away.roster_id, []).append(m.away_score)

    ranking = pr.compute_power_rankings(weekly_scores)
    team_by_roster = {t.roster_id: t for t in league.teams()}

    lines = ["Power Rankings"]
    for pos, (roster_id, score) in enumerate(ranking, start=1):
        team = team_by_roster.get(roster_id)
        if team:
            lines.append(f"{pos:2}. {team.name} ({score:.2f})")
    return "\n".join(lines)


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
