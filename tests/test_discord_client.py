from sleeperbot.discord_client import chunk_message


def test_empty_text_produces_no_chunks():
    assert chunk_message("") == []


def test_short_text_is_a_single_chunk():
    assert chunk_message("hello") == ["hello"]


def test_long_text_splits_under_limit_without_losing_content():
    line = "x" * 100
    text = "\n".join([line] * 50)
    chunks = chunk_message(text, limit=500)
    assert len(chunks) > 1
    assert all(len(chunk) <= 500 for chunk in chunks)
    assert "\n".join(chunks) == text
