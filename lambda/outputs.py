from dataclasses import dataclass
from typing import Any, Sequence, List
import logging
from utils import _to_float, _as_int, _as_float
from models import TransactionRecord, CurrentGoalWrapper, RecruitmentNPO, Sponsor

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FinanceSummary:
    total_budget: float
    total_spent: float
    current_utilization: float
    pending_reimbursements: float

    @staticmethod
    def parse_finance_summary(values: Sequence[Sequence[Any]]) -> FinanceSummary:
        """
        Example parser for a "Dashboard" range like A1:D20.

        Common pattern: a key/value table, e.g.
        ["Total Budget", "1234.56"]
        ["Total Spent", "789.00"]
        ...
        """
        # Turn 2-column rows into a map: label -> value
        kv: dict[str, Any] = {}
        for row in values:
            if len(row) >= 2 and row[0] is not None:
                kv[str(row[0]).strip().lower()] = row[1]

        total_budget = _to_float(kv.get("total budget"))
        total_spent = _to_float(kv.get("total spent"))
        pending = _to_float(kv.get("pending reimbursements"))

        utilization = (total_spent / total_budget) if total_budget else 0.0

        return FinanceSummary(
            total_budget=total_budget,
            total_spent=total_spent,
            current_utilization=utilization,
            pending_reimbursements=pending,
        )


@dataclass(frozen=True)
class FinanceTrajectory:
    week: int
    week_ending: str
    actual_spend: float
    prijected_spend: float
    variance: float
    top_spending_category: str

    @staticmethod
    def parse_finance_trajectory(
        values: Sequence[Sequence[Any]],
    ) -> Sequence[FinanceTrajectory]:
        """
        Example parser for a "Trajectory" range like A1:F52.

        Expected columns:
        Week | Week Ending | Actual Spend | Projected Spend | Variance | Top Spending Category
        """
        trajectories: list[FinanceTrajectory] = []

        for i, row in enumerate(values):
            if len(row) < 6:
                continue  # Skip incomplete rows

            try:
                week = int(row[0])
                week_ending = str(row[1]).strip()
                actual_spend = _to_float(row[2])
                projected_spend = _to_float(row[3])
                variance = _to_float(row[4])
                top_category = str(row[5]).strip()

                trajectory = FinanceTrajectory(
                    week=week,
                    week_ending=week_ending,
                    actual_spend=actual_spend,
                    prijected_spend=projected_spend,
                    variance=variance,
                    top_spending_category=top_category,
                )
                trajectories.append(trajectory)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid finance trajectory row {i}: {row}. Error: {e}"
                )
                continue  # Skip rows with invalid data

        return trajectories


@dataclass(frozen=True)
class FinanceTransactions:
    transactions: List[TransactionRecord]

    @staticmethod
    def parse_finance_transactions(
        values: Sequence[Sequence[Any]],
    ) -> FinanceTransactions:
        """
        Example parser for a "Transactions" range like A1:E1000.

        Expected columns:
        Date | Transaction ID	| Description | Category | Stakeholder/Team | Amount | Type | Status |Receipt Link
        """
        transactions: List[TransactionRecord] = []

        for i, row in enumerate(values):
            if len(row) < 5:
                continue  # Skip incomplete rows

            try:
                date = str(row[0]).strip()
                transaction_id = str(row[1]).strip()
                description = str(row[2]).strip()
                category = str(row[3]).strip()
                team = str(row[4]).strip()
                amount = _to_float(row[5])
                type_ = str(row[6]).strip() if len(row) > 6 else ""
                status = str(row[7]).strip() if len(row) > 7 else ""
                receipt_link = str(row[8]).strip() if len(row) > 8 else ""

                record = TransactionRecord(
                    date=date,
                    transaction_id=transaction_id,
                    description=description,
                    category=category,
                    stakeholder=team,
                    amount=amount,
                    type=type_,
                    status=status,
                    receipt_link=receipt_link,
                )
                transactions.append(record)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid transaction row {i}: {row}. Error: {e}"
                )
                continue  # Skip rows with invalid data

        return FinanceTransactions(transactions=transactions)


@dataclass(frozen=True)
class RecruitmentSummary:
    npos_contacted: CurrentGoalWrapper[int]
    npos_recruited: CurrentGoalWrapper[int]
    sponsors_contacted: CurrentGoalWrapper[int]
    sponsorship_secured: CurrentGoalWrapper[float]
    applicatuibs_received: CurrentGoalWrapper[int]
    challenges_submitted: CurrentGoalWrapper[int]

    @staticmethod
    def parse_recruitment_summary(
        values: Sequence[Sequence[Any]],
    ) -> RecruitmentSummary:
        """
        Example parser for a "Recruitment Dashboard" range like A1:D20.

        Common pattern: a key/value table, e.g.
        ["NPOs Contacted", "50", "100"]
        ["NPOs Recruited", "30", "80"]
        ...
        """
        # Turn 2 or 3-column rows into a map: label -> (current, goal)
        kv: dict[str, tuple[Any, Any]] = {}
        for row in values:
            if len(row) >= 2 and row[0] is not None:
                current = row[1]
                goal = row[2] if len(row) >= 3 else None
                kv[str(row[0]).strip().lower()] = (current, goal)

        def to_current_goal(label: str) -> CurrentGoalWrapper[int]:
            current, goal = kv.get(label, (0, 0))
            return CurrentGoalWrapper(
                current=_as_int(current, 0),
                goal=_as_int(goal, 0),
            )

        def to_current_goal_float(label: str) -> CurrentGoalWrapper[float]:
            current, goal = kv.get(label, (0.0, 0.0))
            return CurrentGoalWrapper(
                current=_as_float(current, 0.0),
                goal=_as_float(goal, 0.0),
            )

        return RecruitmentSummary(
            npos_contacted=to_current_goal("npos contacted"),
            npos_recruited=to_current_goal("npos recruited"),
            sponsors_contacted=to_current_goal("sponsors contacted"),
            sponsorship_secured=to_current_goal_float("sponsorship secured"),
            applicatuibs_received=to_current_goal("applications received"),
            challenges_submitted=to_current_goal("challenges submitted"),
        )


class RecruitmentNPO_CRM:
    npos: List[RecruitmentNPO]

    @staticmethod
    def parse_npo_crm(
        values: Sequence[Sequence[Any]],
    ) -> List[RecruitmentNPO]:
        """
        Example parser for a "NPO CRM" range like A1:E1000.

        Expected columns:
        NPO Name | Contact Name | Email | Status | Initial Contact Date | Last Contact Date | Source | LinkedIn | Website | Link to Notes (Granola)
        """
        npos: List[RecruitmentNPO] = []

        for i, row in enumerate(values):
            if len(row) < 10:
                continue

            try:
                npo_name = str(row[0]).strip()
                contact_name = str(row[1]).strip()
                email = str(row[2]).strip()
                status = str(row[3]).strip()
                inital_contact_date = str(row[4]).strip()
                last_contact_date = str(row[5]).strip()
                source = str(row[6]).strip()
                linkedin = str(row[7]).strip()
                website = str(row[8]).strip()
                link_to_notes = str(row[9]).strip()
                npo = RecruitmentNPO(
                    npo_name=npo_name,
                    contact_name=contact_name,
                    email=email,
                    status=status,
                    initial_contact_date=inital_contact_date,
                    last_contact_date=last_contact_date,
                    source=source,
                    website=website,
                    linkedin=linkedin,
                    link_to_notes=link_to_notes,
                )

                npos.append(npo)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid NPO CRM row {i}: {row}. Error: {e}"
                )
                continue  # Skip rows with invalid data

        return npos


class RecruitmentSponsor_CRM:
    sponsors: List[Sponsor]

    @staticmethod
    def parse_sponsor_crm(
        values: Sequence[Sequence[Any]],
    ) -> List[Sponsor]:
        """
        Example parser for a "Sponsor CRM" range like A1:E1000.

        Expected columns:
        Company | Source | Event Sponsored | Contact Name | Contact email | LinkedIn | Initial Contact Date | Last Contact Date | Pledged ($) | Stevens Event Date | Link to Notes
        """
        sponsors: List[Sponsor] = []

        for i, row in enumerate(values):
            if len(row) < 10:
                continue

            try:
                company = str(row[0]).strip()
                source = str(row[1]).strip()
                event_sponsored = str(row[2]).strip()
                contact_name = str(row[3]).strip()
                contact_email = str(row[4]).strip()
                linkedin = str(row[5]).strip()
                initial_contact_date = str(row[6]).strip()
                last_contact_date = str(row[7]).strip()
                pledged = _to_float(row[8])
                stevens_event_date = str(row[9]).strip()
                link_to_notes = str(row[10]).strip()

                sponsor = Sponsor(
                    company=company,
                    source=source,
                    event_sponsored=event_sponsored,
                    contact_name=contact_name,
                    contact_email=contact_email,
                    linkedin=linkedin,
                    initial_contact_date=initial_contact_date,
                    last_contact_date=last_contact_date,
                    pledged=pledged,
                    stevens_event_date=stevens_event_date,
                    link_to_notes=link_to_notes,
                )

                sponsors.append(sponsor)
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Skipping invalid sponsor CRM row {i}: {row}. Error: {e}"
                )
                continue  # Skip rows with invalid data

        return sponsors
