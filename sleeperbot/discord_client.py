import requests

# Discord hard-caps message content at 2000 characters.
DISCORD_MESSAGE_LIMIT = 2000


def chunk_message(text, limit=DISCORD_MESSAGE_LIMIT):
    if not text:
        return []

    chunks = []
    current = ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def send_message(webhook_url, text):
    for chunk in chunk_message(text):
        response = requests.post(webhook_url, json={"content": chunk}, timeout=10)
        response.raise_for_status()
