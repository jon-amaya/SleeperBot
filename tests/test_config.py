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
    config = load_config()
    assert config["close_scores_threshold"] == 15.0
    assert config["daily_waiver"] is False
