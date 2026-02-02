import urllib.request


def send_discord_message(webhook_url: str, message: str) -> None:
    """Sends a message to a Discord channel via webhook."""
    data = {"content": message}
    req = urllib.request.Request(
        webhook_url,
        data=bytes(str(data), encoding="utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as response:
        response.read()
