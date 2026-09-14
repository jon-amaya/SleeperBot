from sleeperbot.discord_bot import report_text


def test_report_text_passes_through_nonempty_text():
    assert report_text(lambda league: "Current Standings\n1: Alpha", league=None) == "Current Standings\n1: Alpha"


def test_report_text_falls_back_when_empty():
    assert report_text(lambda league: "", league=None) == "Nothing to report."
