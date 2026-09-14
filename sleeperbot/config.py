import os


class ConfigError(Exception):
    pass


def _str_to_bool(value, default=False):
    if value is None or value == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def load_config():
    league_id = os.environ.get("SLEEPER_LEAGUE_ID")
    if not league_id:
        raise ConfigError("SLEEPER_LEAGUE_ID is required")

    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise ConfigError("DISCORD_WEBHOOK_URL is required")

    return {
        "league_id": league_id,
        "webhook_url": webhook_url,
        "timezone": os.environ.get("TIMEZONE", "America/New_York"),
        "start_date": os.environ.get("START_DATE", "2026-09-10"),
        "end_date": os.environ.get("END_DATE", "2027-01-10"),
        "close_scores_threshold": float(os.environ.get("CLOSE_SCORES_THRESHOLD", "15")),
        "daily_waiver": _str_to_bool(os.environ.get("DAILY_WAIVER")),
        "init_msg": os.environ.get("INIT_MSG", ""),
    }
