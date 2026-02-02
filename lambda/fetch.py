from clients import SheetsClient
from models import FinanceSheet, FinanceConfig, RecruitmentSheet, RecruitmentConfig
from configs import FINANCE_SPECS, RECRUITMENT_SPECS
import logging

logger = logging.getLogger(__name__)


def fetch_finance_sheet(
    client: SheetsClient,
    cfg: FinanceConfig,
    sheet: FinanceSheet,
):
    logger.info(f"Fetching finance sheet: {sheet.value}")
    sheet_cfg = cfg.get(sheet)

    raw = client.get_values(cfg.spreadsheet_id, sheet_cfg.full_range)
    logger.info(f"Fetched {len(raw)} rows for finance sheet: {sheet.value}")

    spec = FINANCE_SPECS.get(sheet)
    if spec is None:
        logger.error(f"No parser registered for finance sheet: {sheet}")
        raise KeyError(f"No parser registered for {sheet}")

    return spec.parse(raw)


def fetch_recruitment_sheet(
    client: SheetsClient,
    cfg: RecruitmentConfig,
    sheet: RecruitmentSheet,
):
    logger.info(f"Fetching recruitment sheet: {sheet.value}")
    sheet_cfg = cfg.get(sheet)

    raw = client.get_values(cfg.spreadsheet_id, sheet_cfg.full_range)
    logger.info(f"Fetched {len(raw)} rows for finance sheet: {sheet.value}")

    spec = RECRUITMENT_SPECS.get(sheet)
    if spec is None:
        logger.error(f"No parser registered for recruitment sheet: {sheet}")
        raise KeyError(f"No parser registered for {sheet}")

    return spec.parse(raw)
