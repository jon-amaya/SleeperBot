import pytest

from sleeperbot.config import ConfigError, load_config


def test_missing_league_id_raises(monkeypatch):
    monkeypatch.delenv("SLEEPER_LEAGUE_ID", raising=False)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    with pytest.raises(ConfigError):
        load_config()


def test_missing_webhook_raises(monkeypatch):
    monkeypatch.setenv("SLEEPER_LEAGUE_ID", "12345")
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    with pytest.raises(ConfigError):
        load_config()


def test_defaults_applied(monkeypatch):
    monkeypatch.setenv("SLEEPER_LEAGUE_ID", "12345")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.delenv("CLOSE_SCORES_THRESHOLD", raising=False)
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("DISCORD_GUILD_ID", raising=False)
    config = load_config()
    assert config["close_scores_threshold"] == 15.0
    assert config["bot_token"] is None
    assert config["guild_id"] is None


def test_bot_token_and_guild_id_are_optional_and_pass_through(monkeypatch):
    monkeypatch.setenv("SLEEPER_LEAGUE_ID", "12345")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.example/webhook")
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "fake-token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "999")
    config = load_config()
    assert config["bot_token"] == "fake-token"
    assert config["guild_id"] == "999"
