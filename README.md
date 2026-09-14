# SleeperBot

A self-hosted Discord bot for a Sleeper fantasy football league. It polls
[Sleeper's free public API](https://docs.sleeper.com/) on a schedule and posts
standings, matchups, close scores, trophies, power rankings, and waiver
reports to a Discord channel via webhook.

It's outbound-only: no inbound port, no web server, no reverse proxy needed.
It just wakes up on a cron schedule, fetches data, and posts a message.

## Setup

1. **Find your league ID.** Open your league in the Sleeper app/website; the
   URL looks like `sleeper.app/leagues/<LEAGUE_ID>/...`. Your league must be
   for the season you want to track (Sleeper leagues are one per season).
2. **Create a Discord webhook.** In your Discord server: Channel Settings →
   Integrations → Webhooks → New Webhook → Copy Webhook URL.
3. Fill in `SLEEPER_LEAGUE_ID` and `DISCORD_WEBHOOK_URL` in `docker-compose.yml`.
4. `docker compose up -d --build`

On a Raspberry Pi, just run the same command there — `python:3.12-slim` is a
multi-arch base image, so no cross-compilation is needed.

## Environment variables

| Variable | Required | Default | Notes |
|---|---|---|---|
| `SLEEPER_LEAGUE_ID` | yes | - | From your league's URL |
| `DISCORD_WEBHOOK_URL` | yes | - | Discord channel webhook |
| `TIMEZONE` | no | `America/New_York` | Used for most scheduled posts |
| `START_DATE` | no | `2026-09-10` | Scheduler start |
| `END_DATE` | no | `2027-01-10` | Scheduler end |
| `CLOSE_SCORES_THRESHOLD` | no | `15` | Point difference still called "close" |
| `DAILY_WAIVER` | no | `false` | Post waiver report daily instead of just Wednesday |
| `INIT_MSG` | no | (empty) | Message posted once on startup |
| `DISCORD_BOT_TOKEN` | no | - | Enables live slash commands (see below) |
| `DISCORD_GUILD_ID` | no | - | Instant slash-command sync to one server while testing |

## Enabling slash commands

By default SleeperBot only pushes scheduled reports via the webhook. Setting
`DISCORD_BOT_TOKEN` additionally starts a live bot that responds to
`/standings`, `/matchups`, `/scoreboard`, `/close_scores`, `/trophies`,
`/power_rankings`, `/waiver_report`, and `/monitor` typed directly in Discord
— on top of, not instead of, the scheduled webhook posts. Anyone in the server
can run them and replies post publicly to the channel.

One-time setup in the [Discord Developer Portal](https://discord.com/developers/applications):

1. **New Application** (or reuse an existing one).
2. **Bot** tab → **Add Bot** → copy the token → `DISCORD_BOT_TOKEN`.
3. **OAuth2 → URL Generator** → scopes `bot` + `applications.commands`,
   permission `Send Messages` → open the generated URL to invite it to your
   server.
4. *(Optional, for instant command sync while testing)* right-click your
   server in Discord → **Copy Server ID** → `DISCORD_GUILD_ID`. Without this,
   commands still work, but can take up to an hour to appear globally after
   startup.

## Reports

Message formats follow
[dtcarls/fantasy_football_chat_bot](https://github.com/dtcarls/fantasy_football_chat_bot),
the project GameDayBot grew out of — a header line plus rows, as plain text.

| Report | When | Notes |
|---|---|---|
| Score update | Fri & Mon 7:30am, Sun 4pm & 8pm | Bars scaled to the week's high score |
| Final score + trophies | Tue 7:30am | Last week's results |
| Standings | Wed 7:30am | With a playoff line at your league's cutoff |
| Waiver report | Wed 7:31am (or daily) | FAAB amounts when the league uses them |
| Matchups | Thu 7:30pm | |
| Players to monitor | Sun 7:30am | Injured starters, from Sleeper's player feed |
| Close scores | Mon 6:30pm | Within `CLOSE_SCORES_THRESHOLD` |
| Power rankings | Tue 6:30pm | Two-step dominance: 80% all-play, 15% points, 5% margin |

Trophies awarded: 👑 high score, 💩 low score, 😱 blowout, 😅 close win,
🍀 lucky, 😡 unlucky, 🤖 best manager, 🤡 worst manager.

## What's not supported (and why)

Sleeper's free public API has no player projections and no playoff-odds
simulation, both of which ESPN provides. So compared to ESPN-based bots:

- No projected scoreboard — only actual and live scores
- No over/under-achiever trophies, which compare actual against projected
- Power rankings carry no playoff-odds percentage

Everything else ports over. The injury monitor actually works *better* here:
Sleeper's player feed carries `injury_status` directly, with no scraping.

## Development

```
pip install -r requirements-dev.txt
pytest
```

Run a single report manually against your real league without waiting for
the scheduler:

```
python -c "from sleeperbot.bot import bot; bot('get_standings')"
```
