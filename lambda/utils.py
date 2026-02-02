from typing import Any
import re
import os
import logging
import logging
import json
import boto3

_CURRENCY_RE = re.compile(r"[,\s$]")
CONFIG_SECRET_ARN = "METRICS_CONFIG_SECRET_ARN"

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

secrets_client = boto3.client("secretsmanager")


def safe_get_env(var_name: str) -> str:
    value = os.environ.get(var_name)
    if value is None:
        logger.error(f"Environment variable {var_name} not set")
        raise EnvironmentError(f"Environment variable {var_name} not set")
    return value


def is_var_in_env(var_name: str) -> bool:
    return var_name in os.environ


def load_config_from_secrets() -> dict:
    secret_arn = safe_get_env(CONFIG_SECRET_ARN)
    try:
        logger.info(f"Fetching secret value from ARN: {secret_arn}")
        response = secrets_client.get_secret_value(SecretId=secret_arn)
        secret_string = response.get("SecretString")
        config_data = json.loads(secret_string)
        logger.info("Successfully loaded configuration from Secrets Manager")
        return config_data
    except Exception as e:
        logger.error(f"Error fetching secret from Secrets Manager: {e}")
        raise


def load_config_from_file(file_path: str) -> dict:
    with open(file_path, "r") as f:
        return json.load(f)


def _to_float(x: Any) -> float:
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("$", "")
    return float(s) if s else 0.0


def _as_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return default
        s = s.replace(",", "")
        return int(s)
    return int(value)


def _as_float(value: Any, default: float) -> float:
    if value is None:
        return default

    # If Sheets returns already-numeric
    if isinstance(value, (int, float)):
        return float(value)

    s = str(value).strip()
    if s == "":
        return default

    # Common "empty" sentinels in sheets
    if s.lower() in {"n/a", "na", "none", "null", "-", "—"}:
        return default

    # Parentheses as negative accounting format: ($500) => -500
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    # Remove $, commas, spaces
    s = _CURRENCY_RE.sub("", s)

    # Optional: handle percent (e.g., "12%" -> 12.0 or 0.12 depending on what you want)
    if s.endswith("%"):
        s = s[:-1]
        # choose ONE behavior:
        # return float(s) / 100.0
        return float(s)

    try:
        num = float(s)
        return -num if negative else num
    except ValueError:
        return default
