from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Mapping, TypeVar, Callable, Sequence, Any, List, Set
from dataclasses import dataclass, field


class FinanceSheet(Enum):
    SUMMARY = "summary"
    TRAJECTORY = "trajectory"
    TRANSACTIONS = "transactions"


class RecruitmentSheet(Enum):
    SUMMARY = "summary"
    NPO_CRM = "npo_crm"
    SPONSORS_CRM = "sponsors_crm"


@dataclass(frozen=True)
class SheetConfig:
    sheet_name: str
    sheet_range: str

    def __post_init__(self) -> None:
        if "!" in self.sheet_name:
            raise ValueError("sheet_name must not contain '!'")
        if not self.sheet_range:
            raise ValueError("sheet_range cannot be empty")

    @property
    def full_range(self) -> str:
        return f"{self.sheet_name}!{self.sheet_range}"


T = TypeVar("T")


@dataclass(frozen=True)
class SheetSpec(Generic[T]):
    parse: Callable[[Sequence[Sequence[Any]]], T]


SheetKey = TypeVar("SheetKey", bound=Enum)


@dataclass(frozen=True)
class SpreadsheetConfig(Generic[SheetKey]):
    spreadsheet_id: str
    sheet_configs: Mapping[SheetKey, SheetConfig]

    def get(self, key: SheetKey) -> SheetConfig:
        return self.sheet_configs[key]

    def full_range(self, key: SheetKey) -> str:
        return self.sheet_configs[key].full_range


@dataclass(frozen=True)
class SheetsValues:
    range: str
    values: Sequence[Sequence[str]]


@dataclass(frozen=True)
class TransactionRecord:
    date: str
    transaction_id: str
    description: str
    category: str
    stakeholder: str
    amount: float
    type: str
    status: str
    receipt_link: str


@dataclass(frozen=True)
class CurrentGoalWrapper(Generic[T]):
    current: T
    goal: T


@dataclass(frozen=True)
class RecruitmentNPO:
    npo_name: str
    contact_name: str
    email: str
    status: str
    initial_contact_date: str
    last_contact_date: str
    source: str
    website: str
    linkedin: str
    link_to_notes: str


@dataclass(frozen=True)
class Sponsor:
    company: str
    source: str
    event_sponsored: str
    contact_name: str
    contact_email: str
    linkedin: str
    initial_contact_date: str
    last_contact_date: str
    pledged: float
    stevens_event_date: str
    link_to_notes: str


FinanceConfig = SpreadsheetConfig[FinanceSheet]
RecruitmentConfig = SpreadsheetConfig[RecruitmentSheet]


@dataclass(frozen=True)
class GithubSettings:
    npo_label: str
    stale_pr_days: int
    stale_issue_days: int


@dataclass(frozen=True)
class TeamConfig:
    repos: List[str]
    members: List[str]
    tech_leads: List[str]


@dataclass(frozen=True)
class GithubConfig:
    organization: str
    teams: Mapping[str, TeamConfig]
    settings: GithubSettings


@dataclass(frozen=True)
class VelocityMetrics:
    merged_prs: int
    avg_cycle_time: float
    issues_closed: int


@dataclass(frozen=True)
class ParticipationMetrics:
    active_contributors: int
    total_members: int
    participation_rate: float
    non_lead_reviews: int


@dataclass(frozen=True)
class NPOMetrics:
    features_shipped: int
    avg_time_to_deliver: float


@dataclass(frozen=True)
class AlertMetrics:
    stale_prs: List[str]
    stale_issues: List[str]


@dataclass(frozen=True)
class TeamReport:
    team_name: str
    velocity: VelocityMetrics
    participation: ParticipationMetrics
    npo_impact: NPOMetrics
    alerts: AlertMetrics
    start_date: str
    end_date: str


@dataclass
class RawTeamMetrics:
    velocity_merged_prs: int = 0
    velocity_issues_closed: int = 0
    velocity_cycle_times: List[float] = field(default_factory=list)
    participation_pr_authors: Set[str] = field(default_factory=set)
    participation_non_lead_reviews: int = 0
    npo_features_closed: int = 0
    npo_time_to_close: List[float] = field(default_factory=list)
    alerts_stale_prs: List[str] = field(default_factory=list)
    alerts_stale_issues: List[str] = field(default_factory=list)
