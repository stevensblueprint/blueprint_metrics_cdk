import urllib.request
import logging
import json

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_discord_message(webhook_url: str, message: str) -> None:
    """Sends a message to a Discord channel via webhook."""
    data = {"content": message}
    payload = json.dumps(data).encode("utf-8")
    logger.info(f"Discord payload: {payload}")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "BlueprintMetricsLambda/1.0",
        },
    )
    try:
        urllib.request.urlopen(req)
        logger.info("Discord message sent successfully.")
    except Exception as e:
        logger.error(f"Failed to send Discord message: {e}", exc_info=True)
        raise
