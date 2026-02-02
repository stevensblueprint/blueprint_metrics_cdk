from outputs import (
    FinanceSummary,
    FinanceTrajectory,
    FinanceTransactions,
    RecruitmentSummary,
    RecruitmentNPO_CRM,
    RecruitmentSponsor_CRM,
)
from models import FinanceSheet, SheetSpec, RecruitmentSheet

FINANCE_SPECS: dict[FinanceSheet, SheetSpec[object]] = {
    FinanceSheet.SUMMARY: SheetSpec(parse=FinanceSummary.parse_finance_summary),
    FinanceSheet.TRAJECTORY: SheetSpec(
        parse=FinanceTrajectory.parse_finance_trajectory
    ),
    FinanceSheet.TRANSACTIONS: SheetSpec(
        parse=FinanceTransactions.parse_finance_transactions
    ),
}

RECRUITMENT_SPECS: dict[RecruitmentSheet, SheetSpec[object]] = {
    RecruitmentSheet.SUMMARY: SheetSpec(
        parse=RecruitmentSummary.parse_recruitment_summary
    ),
    RecruitmentSheet.NPO_CRM: SheetSpec(parse=RecruitmentNPO_CRM.parse_npo_crm),
    RecruitmentSheet.SPONSORS_CRM: SheetSpec(
        parse=RecruitmentSponsor_CRM.parse_sponsor_crm
    ),
}
