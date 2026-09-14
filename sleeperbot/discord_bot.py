import asyncio
import logging

import discord
from discord import app_commands

from sleeperbot import formatting
from sleeperbot.discord_client import build_embeds
from sleeperbot.league import SleeperLeague
from sleeperbot.sleeper_client import SleeperClient

logger = logging.getLogger(__name__)


def report_text(build_fn, league):
    """Build a report's text, falling back to a friendly placeholder when empty
    (e.g. build_waiver_report on a quiet day)."""
    text = build_fn(league)
    return text if text else "Nothing to report."


def _build_league(config):
    return SleeperLeague(SleeperClient(config["league_id"]))


class SleeperBotClient(discord.Client):
    def __init__(self, config):
        super().__init__(intents=discord.Intents.default())
        self.config = config
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self):
        config = self.config
        tree = self.tree

        async def respond(interaction, build_fn, style_key):
            await interaction.response.defer()
            try:
                league = await asyncio.to_thread(_build_league, config)
                text = await asyncio.to_thread(report_text, build_fn, league)
                footer = f"{league.name} • {league.season}"
            except Exception:
                logger.exception("Slash command failed while building a report")
                await interaction.followup.send("Something went wrong generating that report.")
                return

            title, color, monospace = formatting.REPORT_STYLE.get(
                style_key, formatting.DEFAULT_STYLE
            )
            payloads = build_embeds(
                title, formatting.strip_header(text), color, monospace, footer=footer
            )
            for payload in payloads:
                embed = discord.Embed(
                    title=payload.get("title"),
                    description=payload["description"],
                    color=payload["color"],
                )
                if "footer" in payload:
                    embed.set_footer(text=payload["footer"]["text"])
                await interaction.followup.send(embed=embed)

        @tree.command(name="standings", description="Current league standings")
        async def standings(interaction: discord.Interaction):
            await respond(interaction, formatting.build_standings, "get_standings")

        @tree.command(name="matchups", description="This week's matchups")
        async def matchups(interaction: discord.Interaction):
            await respond(interaction, formatting.build_matchups, "get_matchups")

        @tree.command(name="scoreboard", description="This week's live/final scores")
        async def scoreboard(interaction: discord.Interaction):
            await respond(interaction, formatting.build_scoreboard, "get_scoreboard")

        @tree.command(name="close_scores", description="This week's close scores")
        async def close_scores(interaction: discord.Interaction):
            await respond(
                interaction,
                lambda league: formatting.build_close_scores(
                    league, threshold=config["close_scores_threshold"]
                ),
                "get_close_scores",
            )

        @tree.command(name="trophies", description="This week's trophies")
        async def trophies(interaction: discord.Interaction):
            await respond(interaction, formatting.build_trophies, "get_trophies")

        @tree.command(name="power_rankings", description="Current power rankings")
        async def power_rankings(interaction: discord.Interaction):
            await respond(interaction, formatting.build_power_rankings, "get_power_rankings")

        @tree.command(name="waiver_report", description="Today's waiver wire moves")
        async def waiver_report(interaction: discord.Interaction):
            await respond(interaction, formatting.build_waiver_report, "get_waiver_report")

        @tree.command(name="monitor", description="Injured starters to check before kickoff")
        async def monitor(interaction: discord.Interaction):
            await respond(interaction, formatting.build_monitor, "get_monitor")

    async def setup_hook(self):
        guild_id = self.config.get("guild_id")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Slash commands synced to guild %s", guild_id)
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally (may take up to an hour to appear)")

    async def on_ready(self):
        logger.info("Logged in as %s", self.user)


def run(config):
    client = SleeperBotClient(config)
    client.run(config["bot_token"], log_handler=None)
