"""
Chart images for the reports that carry one.

Everything renders headless through matplotlib's Agg backend -- the container
has no display -- and returns PNG bytes, which discord_client uploads as an
attachment the embed then references.
"""

import io

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402  (must follow the backend choice)

# Tuned to sit inside a Discord embed rather than glare out of it: the figure
# ground matches the embed card, the axes the code-block inset.
BACKGROUND = "#2b2d31"
PANEL = "#1e1f22"
INK = "#dbdee1"
MUTED = "#8b949e"
GRID = "#3a3d44"

# Enough distinct hues for a 12-team league, readable on a dark ground.
SERIES_COLORS = [
    "#f0a830", "#5ac37d", "#6aa6d8", "#e0625e", "#b98be0", "#4bc0c0",
    "#e89ac7", "#a8b545", "#d98f45", "#7f8fa6", "#56b6c2", "#c678dd",
]

FIGSIZE = (9, 4.5)
DPI = 130


def _figure():
    fig, ax = plt.subplots(figsize=FIGSIZE, dpi=DPI)
    fig.patch.set_facecolor(BACKGROUND)
    ax.set_facecolor(PANEL)
    ax.grid(True, color=GRID, linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=8)
    return fig, ax


def _render(fig, ax, title, ylabel=None, legend=True):
    ax.set_title(title, color=INK, fontsize=11, pad=10, loc="left")
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
    ax.set_xlabel("Week", color=MUTED, fontsize=9)
    if legend:
        leg = ax.legend(
            loc="center left", bbox_to_anchor=(1.01, 0.5),
            fontsize=7.5, frameon=False, labelcolor=INK,
        )
        if leg:
            leg.set_title(None)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()


def _series_color(index):
    return SERIES_COLORS[index % len(SERIES_COLORS)]


def weekly_scores_chart(weeks, team_names):
    """Points scored per team, week by week. weeks: {week: {roster_id: score}}."""
    if not weeks:
        return None
    fig, ax = _figure()
    ordered = sorted(weeks)
    for index, (roster_id, name) in enumerate(team_names.items()):
        points = [weeks[w].get(roster_id) for w in ordered]
        ax.plot(ordered, points, marker="o", markersize=2.5, linewidth=1.6,
                color=_series_color(index), label=name)
    ax.set_xticks(ordered)
    return _render(fig, ax, "Weekly scores", ylabel="Points")


def rank_trend_chart(weeks, team_names, title):
    """
    Rank by week, drawn with first place at the top. weeks: {week: {roster_id:
    rank}} -- used for both the standings and power-rankings trends.
    """
    if not weeks:
        return None
    fig, ax = _figure()
    ordered = sorted(weeks)
    for index, (roster_id, name) in enumerate(team_names.items()):
        ranks = [weeks[w].get(roster_id) for w in ordered]
        ax.plot(ordered, ranks, marker="o", markersize=2.5, linewidth=1.6,
                color=_series_color(index), label=name)
    ax.invert_yaxis()
    ax.set_xticks(ordered)
    ax.set_yticks(range(1, len(team_names) + 1))
    return _render(fig, ax, title, ylabel="Rank")


def bad_management_chart(totals, team_names):
    """Points left on the bench across the season, worst first."""
    if not totals:
        return None
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    labels = [team_names.get(rid, str(rid)) for rid, _ in ranked]
    values = [value for _, value in ranked]

    fig, ax = _figure()
    bars = ax.barh(labels, values, color="#e0625e", height=0.62)
    ax.invert_yaxis()
    ax.grid(True, axis="x", color=GRID, linewidth=0.6, alpha=0.8)
    ax.grid(False, axis="y")
    for bar, value in zip(bars, values):
        ax.text(bar.get_width() + max(values) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.0f}", va="center", color=MUTED, fontsize=8)
    ax.tick_params(axis="y", labelsize=8, colors=INK)
    ax.set_title("Points left on the bench", color=INK, fontsize=11, pad=10, loc="left")
    ax.set_xlabel("Points", color=MUTED, fontsize=9)
    fig.tight_layout()

    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return buffer.getvalue()
