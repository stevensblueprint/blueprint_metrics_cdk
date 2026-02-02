from clients import SheetsClient, GithubClient
from parser import parse_config
import json
import logging
from models import (
    FinanceSheet,
    RecruitmentSheet,
    FinanceConfig,
    RecruitmentConfig,
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
    github_service: GithubService, result_store: ThreadSafeResultStore
) -> None:
    logger.info("Generating weekly GitHub metrics")
    reports = github_service.generate_weekly_metrics()
    for report in reports:
        logger.info(f"Metrics computed for team: {report.team_name}")
        result_store.store(report.team_name, report)
    logger.info("Completed GitHub metrics generation")


def handler(event, context):
    logger.info("Starting metrics collection...")
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
        results_store = ThreadSafeResultStore()

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(
                    get_finance_metrics, sheets_client, finance_cfg, results_store
                ): "finance",
                executor.submit(
                    get_recruitment_metrics,
                    sheets_client,
                    recruitment_cfg,
                    results_store,
                ): "recruitment",
                executor.submit(
                    get_github_metrics, github_service, results_store
                ): "github",
            }

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

        webhook_url = safe_get_env("DISCORD_WEBHOOK_URL")
        for key, result in all_results.items():
            message = f"**{key}**: {result}"
            if len(message) > 2000:
                message = message[:1997] + "..."
            send_discord_message(webhook_url=webhook_url, message=message)

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


if __name__ == "__main__":
    handler(None, None)
