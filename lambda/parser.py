from typing import Any, Dict, Mapping, Type, TypeVar
from enum import Enum
import logging
from models import (
    SheetConfig,
    SpreadsheetConfig,
    RecruitmentSheet,
    FinanceSheet,
    RecruitmentConfig,
    FinanceConfig,
    GithubConfig,
    TeamConfig,
    GithubSettings,
)

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)


def _parse_github_config(raw: Mapping[str, Any]) -> GithubConfig:
    try:
        organization = raw["organization"]
        settings_raw = raw["settings"]
        teams_raw = raw["teams"]
    except KeyError as e:
        logger.error(f"Missing required key in github config: {e}")
        raise ValueError(f"Missing required key in github config: {e}") from e

    settings = GithubSettings(
        npo_label=settings_raw.get("npo_label", "NPO-Feature"),
        stale_pr_days=settings_raw.get("stale_pr_days", 7),
        stale_issue_days=settings_raw.get("stale_issue_days", 10),
    )

    teams: Dict[str, TeamConfig] = {}
    for team_name, team_data in teams_raw.items():
        try:
            teams[team_name] = TeamConfig(
                repos=team_data.get("repos", []),
                members=team_data.get("members", []),
                tech_leads=team_data.get("tech_leads", []),
            )
        except Exception as e:
            logger.error(f"Error parsing team config for {team_name}: {e}")
            raise

    return GithubConfig(
        organization=organization,
        teams=teams,
        settings=settings,
    )


def _parse_spreadsheet_config(
    raw: Mapping[str, Any],
    *,
    sheet_enum: Type[E],
) -> SpreadsheetConfig[E]:
    """
    Parse a single spreadsheet config section into a SpreadsheetConfig[E].
    """
    try:
        spreadsheet_id = raw["spreadsheet_id"]
    except KeyError as e:
        logger.error(f"Missing spreadsheet_id in config for {sheet_enum.__name__}")
        raise ValueError("Missing required key: spreadsheet_id") from e

    sheet_configs: Dict[E, SheetConfig] = {}

    for key in sheet_enum:
        key_name = key.value
        if key_name not in raw:
            logger.error(f"Missing sheet config '{key_name}' for {sheet_enum.__name__}")
            raise ValueError(
                f"Missing sheet config '{key_name}' for {sheet_enum.__name__}"
            )

        sheet_raw = raw[key_name]

        try:
            sheet_configs[key] = SheetConfig(
                sheet_name=sheet_raw["sheet_name"],
                sheet_range=sheet_raw["sheet_range"],
            )
        except KeyError as e:
            logger.error(
                f"Invalid sheet config for '{key_name}' in {sheet_enum.__name__}: {e}"
            )
            raise ValueError(
                f"Invalid sheet config for '{key_name}', missing {e}"
            ) from e

    allowed_keys = {e.value for e in sheet_enum} | {"spreadsheet_id"}
    extra_keys = set(raw.keys()) - allowed_keys
    if extra_keys:
        logger.warning(
            f"Unknown sheet keys for {sheet_enum.__name__}: {sorted(extra_keys)}"
        )
        raise ValueError(
            f"Unknown sheet keys for {sheet_enum.__name__}: {sorted(extra_keys)}"
        )

    return SpreadsheetConfig(
        spreadsheet_id=spreadsheet_id,
        sheet_configs=sheet_configs,
    )


def parse_config(
    raw: Mapping[str, Any],
) -> tuple[RecruitmentConfig, FinanceConfig, GithubConfig]:
    """
    Parse the full JSON config and return typed config objects.
    """
    logger.info("Parsing application configuration...")
    try:
        recruitment_raw = raw["recruitment"]
        finance_raw = raw["finance"]
        github_raw = raw["github"]
    except KeyError as e:
        logger.error("Config missing 'recruitment' or 'finance' sections")
        raise ValueError(
            "Config must contain 'recruitment' and 'finance' sections"
        ) from e

    recruitment_config: RecruitmentConfig = _parse_spreadsheet_config(
        recruitment_raw,
        sheet_enum=RecruitmentSheet,
    )

    finance_config: FinanceConfig = _parse_spreadsheet_config(
        finance_raw,
        sheet_enum=FinanceSheet,
    )
    github_config = _parse_github_config(github_raw)
    logger.info("Configuration parsed successfully.")
    return recruitment_config, finance_config, github_config
