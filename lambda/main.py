from clients import SheetsClient, GithubClient
from parser import parse_config
import json
import logging
from models import (
    FinanceSheet,
    RecruitmentSheet,
    FinanceConfig,
    RecruitmentConfig,
    MetricOutput,
)
from fetch import fetch_finance_sheet, fetch_recruitment_sheet
from services import GithubService
from concurrent.futures import ThreadPoolExecutor, as_completed
from ThreadSafeResultStore import ThreadSafeResultStore
from utils import (
    load_config_from_file,
    load_config_from_secrets,
    is_var_in_env,
    safe_get_env,
)
from discord import send_discord_message

CONFIG_PATH = "config.json"
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_finance_metrics(
    sheets_client: SheetsClient,
    finance_cfg: FinanceConfig,
    result_store: ThreadSafeResultStore,
) -> None:
    for sheet in FinanceSheet:
        logger.info(f"Processing sheet: {sheet}")
        result = fetch_finance_sheet(sheets_client, finance_cfg, sheet)
        result_store.store(sheet.value, result)
        logger.info(f"Completed sheet: {sheet}")
        logger.info(result)


def get_recruitment_metrics(
    sheets_client: SheetsClient,
    recruitment_cfg: RecruitmentConfig,
    result_store: ThreadSafeResultStore,
) -> None:
    for sheet in RecruitmentSheet:
        logger.info(f"Processing sheet: {sheet}")
        result = fetch_recruitment_sheet(sheets_client, recruitment_cfg, sheet)
        result_store.store(sheet.value, result)
        logger.info(f"Completed sheet: {sheet}")
        logger.info(result)


def get_github_metrics(
    github_service: GithubService, result_store: ThreadSafeResultStore, team: str | None = None
) -> None:
    logger.info(f"Generating weekly GitHub metrics{f' for team: {team}' if team else ''}")
    reports = github_service.generate_weekly_metrics(team_name=team)
    for report in reports:
        logger.info(f"Metrics computed for team: {report.team_name}")
        result_store.store(report.team_name, report)
    logger.info("Completed GitHub metrics generation")


def handler(event, context):
    mode = event.get("mode", "all")  # "general" | "teams" | "all"
    team = event.get("team")  # specific team name, only used when mode="teams"
    logger.info(f"Starting metrics collection in mode: {mode}{f', team: {team}' if team else ''}")
    try:
        config_data = (
            load_config_from_secrets()
            if is_var_in_env("PROD")
            else load_config_from_file(CONFIG_PATH)
        )
        recruitment_cfg, finance_cfg, github_cfg = parse_config(config_data)

        sheets_client = SheetsClient()
        github_client = GithubClient()
        github_service = GithubService(github_client, github_cfg)
        results_store = ThreadSafeResultStore[MetricOutput]()

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {}

            if mode in ("general", "all"):
                futures[executor.submit(
                    get_finance_metrics, sheets_client, finance_cfg, results_store
                )] = "finance"
                futures[executor.submit(
                    get_recruitment_metrics,
                    sheets_client,
                    recruitment_cfg,
                    results_store,
                )] = "recruitment"

            if mode in ("teams", "all"):
                futures[executor.submit(
                    get_github_metrics, github_service, results_store, team
                )] = "github"

            results = {}
            errors = []

            for future in as_completed(futures):
                task_name = futures[future]
                try:
                    future.result()
                    results[task_name] = "success"
                    logger.info(f"Task '{task_name}' completed successfully")
                except Exception as e:
                    error_msg = f"Task '{task_name}' failed: {str(e)}"
                    logger.exception(error_msg)
                    results[task_name] = "failed"
                    errors.append(error_msg)

        all_results = results_store.get_all()
        logger.info(all_results)

        default_webhook_url = safe_get_env("DISCORD_WEBHOOK_URL")
        for key, result in all_results.items():
            team_cfg = github_cfg.teams.get(key)
            webhook_url = (
                team_cfg.discord_webhook_url
                if team_cfg and team_cfg.discord_webhook_url
                else default_webhook_url
            )
            send_discord_message(webhook_url=webhook_url, metric=result)

        logger.info("Finished successfully.")
        return {
            "statusCode": 200 if not errors else 500,
            "body": json.dumps(
                {
                    "message": "Metrics collection completed",
                    "results": results,
                    "errors": errors if errors else None,
                }
            ),
        }
    except Exception as e:
        logger.exception("An error occurred during execution.", exc_info=e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "An error occurred", "error": str(e)}),
        }

