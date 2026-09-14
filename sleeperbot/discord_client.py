import requests

# Discord hard-caps message content at 2000 characters and an embed
# description at 4096. A code fence costs 8 of those.
DISCORD_MESSAGE_LIMIT = 2000
EMBED_DESCRIPTION_LIMIT = 4096
CODE_FENCE_OVERHEAD = 8


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


def build_embeds(title, body, color, monospace, footer=None):
    """
    One embed per chunk, so a long report splits across embeds rather than
    being truncated. Only the first carries the title, only the last the footer.
    """
    limit = EMBED_DESCRIPTION_LIMIT - (CODE_FENCE_OVERHEAD if monospace else 0)
    chunks = chunk_message(body, limit) or [body]

    embeds = []
    for index, chunk in enumerate(chunks):
        description = f"```\n{chunk}\n```" if monospace else chunk
        embed = {"description": description, "color": color}
        if index == 0:
            embed["title"] = title
        if footer and index == len(chunks) - 1:
            embed["footer"] = {"text": footer}
        embeds.append(embed)
    return embeds


def send_embeds(webhook_url, embeds):
    # Discord accepts at most 10 embeds per message.
    for start in range(0, len(embeds), 10):
        response = requests.post(
            webhook_url, json={"embeds": embeds[start:start + 10]}, timeout=10
        )
        response.raise_for_status()


def send_message(webhook_url, text):
    for chunk in chunk_message(text):
        response = requests.post(webhook_url, json={"content": chunk}, timeout=10)
        response.raise_for_status()
