import json

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


def attach_image(embeds, name, png):
    """
    Point the last embed at an image that will be uploaded with it. Discord
    resolves attachment:// against the files in the same request.
    """
    if not embeds or not png:
        return None
    embeds[-1]["image"] = {"url": f"attachment://{name}"}
    return (name, png)


def send_embeds(webhook_url, embeds, files=None):
    """
    Files ride along with the first batch, since that is where the embed
    referencing them sits. Discord accepts at most 10 embeds per message.
    """
    for start in range(0, len(embeds), 10):
        batch = embeds[start:start + 10]
        batch_files = files if start == 0 else None

        if batch_files:
            payload = {
                "payload_json": (None, json.dumps({"embeds": batch}), "application/json")
            }
            for index, (name, png) in enumerate(batch_files):
                payload[f"files[{index}]"] = (name, png, "image/png")
            response = requests.post(webhook_url, files=payload, timeout=30)
        else:
            response = requests.post(webhook_url, json={"embeds": batch}, timeout=10)
        response.raise_for_status()


def send_message(webhook_url, text):
    for chunk in chunk_message(text):
        response = requests.post(webhook_url, json={"content": chunk}, timeout=10)
        response.raise_for_status()
