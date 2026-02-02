import logging
import logging
from typing import List, Dict, Tuple
from datetime import datetime, timedelta, timezone
from clients import GithubClient
from models import (
    GithubConfig,
    TeamConfig,
    TeamReport,
    VelocityMetrics,
    ParticipationMetrics,
    NPOMetrics,
    AlertMetrics,
    RawTeamMetrics,
)

logger = logging.getLogger(__name__)
NPO_LABEL = "NPO-Feature"
STALE_PR_DAYS = 7
STALE_ISSUE_DAYS = 10


class GithubService:
    def __init__(self, client: GithubClient, config: GithubConfig):
        self.client = client
        self.config = config

    def _get_team_metrics(
        self,
        team_name: str,
        config: TeamConfig,
        start_date: datetime,
        end_date: datetime,
    ) -> Tuple[RawTeamMetrics, Dict[str, Dict[str, int]]]:
        """
        Retrieves and aggregates GQM metrics for a specific team over a date range.
        """
        logger.info(f"--- Processing {team_name} ---")

        g = self.client.client
        repos = []
        for r in config.repos:
            try:
                repos.append(g.get_repo(r))
            except Exception as e:
                logger.error(f"Error fetching repo {r}: {e}")

        members = set(config.members)
        leads = set(config.tech_leads)
        non_leads = members - leads
        metrics = RawTeamMetrics()

        member_activity = {
            m: {"prs_merged": 0, "prs_opened": 0, "reviews": 0} for m in members
        }

        for repo in repos:
            try:
                prs = repo.get_pulls(state="all", sort="updated", direction="desc")

                for pr in prs:
                    if pr.updated_at.replace(tzinfo=timezone.utc) < start_date:
                        break

                    pr_created = pr.created_at.replace(tzinfo=timezone.utc)
                    pr_closed = (
                        pr.closed_at.replace(tzinfo=timezone.utc)
                        if pr.closed_at
                        else None
                    )
                    is_member_pr = pr.user.login in members

                    # --- Alert: Stale PRs (Open > 7 days) ---
                    if pr.state == "open":
                        days_open = (datetime.now(timezone.utc) - pr_created).days
                        if days_open > STALE_PR_DAYS:
                            metrics.alerts_stale_prs.append(
                                f"{repo.name}#{pr.number} ({days_open} days)"
                            )

                    # --- Metric: PRs Opened this week ---
                    if start_date <= pr_created <= end_date:
                        if is_member_pr:
                            member_activity[pr.user.login]["prs_opened"] += 1
                            metrics.participation_pr_authors.add(pr.user.login)

                    # --- Metric: Velocity (Merged PRs) ---
                    if (
                        pr.merged
                        and pr_closed
                        and (start_date <= pr_closed <= end_date)
                    ):
                        metrics.velocity_merged_prs += 1
                        if is_member_pr:
                            member_activity[pr.user.login]["prs_merged"] += 1

                        # Cycle Time (Open -> Merged)
                        cycle_time = (
                            pr_closed - pr_created
                        ).total_seconds() / 3600  # hours
                        metrics.velocity_cycle_times.append(cycle_time)

                    # --- Metric: Non-Lead Reviews ---
                    for review in pr.get_reviews():
                        rev_date = review.submitted_at.replace(tzinfo=timezone.utc)
                        if start_date <= rev_date <= end_date:
                            reviewer = review.user.login
                            if reviewer in non_leads:
                                metrics.participation_non_lead_reviews += 1
                            if reviewer in members:
                                member_activity[reviewer]["reviews"] += 1
            except Exception as e:
                logger.error(f"Error processing PRs for {repo.name}: {e}")
            try:
                issues = repo.get_issues(state="all", since=start_date)

                for issue in issues:
                    if issue.pull_request:
                        continue

                    issue_created = issue.created_at.replace(tzinfo=timezone.utc)
                    issue_closed = (
                        issue.closed_at.replace(tzinfo=timezone.utc)
                        if issue.closed_at
                        else None
                    )
                    labels = [l.name for l in issue.labels]

                    # --- Alert: Stale Issues (No activity > 10 days) ---
                    if issue.state == "open":
                        days_inactive = (
                            datetime.now(timezone.utc)
                            - issue.updated_at.replace(tzinfo=timezone.utc)
                        ).days
                        if days_inactive > STALE_ISSUE_DAYS:
                            metrics.alerts_stale_issues.append(
                                f"{repo.name}#{issue.number}"
                            )

                    # --- Metric: Issues Closed ---
                    if issue_closed and (start_date <= issue_closed <= end_date):
                        metrics.velocity_issues_closed += 1

                        # NPO Value Check
                        if NPO_LABEL in labels:
                            metrics.npo_features_closed += 1
                            time_to_close = (
                                issue_closed - issue_created
                            ).total_seconds() / 3600  # hours
                            metrics.npo_time_to_close.append(time_to_close)
            except Exception as e:
                logger.error(f"Error processing issues for {repo.name}: {e}")

        return metrics, member_activity

    def generate_weekly_metrics(
        self,
    ) -> List[TeamReport]:
        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)

        logger.info(f"Generating Report: {one_week_ago.date()} to {now.date()}\n")

        reports: List[TeamReport] = []

        for team_name, team_config in self.config.teams.items():
            metrics, member_activity_ = self._get_team_metrics(
                team_name, team_config, one_week_ago, now
            )

            avg_cycle_time = (
                (sum(metrics.velocity_cycle_times) / len(metrics.velocity_cycle_times))
                if metrics.velocity_cycle_times
                else 0.0
            )
            avg_npo_time = (
                (sum(metrics.npo_time_to_close) / len(metrics.npo_time_to_close))
                if metrics.npo_time_to_close
                else 0.0
            )
            participation_rate = (
                (len(metrics.participation_pr_authors) / len(team_config.members)) * 100
                if team_config.members
                else 0.0
            )

            velocity = VelocityMetrics(
                merged_prs=metrics.velocity_merged_prs,
                avg_cycle_time=avg_cycle_time,
                issues_closed=metrics.velocity_issues_closed,
            )

            participation = ParticipationMetrics(
                active_contributors=len(metrics.participation_pr_authors),
                total_members=len(team_config.members),
                participation_rate=participation_rate,
                non_lead_reviews=metrics.participation_non_lead_reviews,
            )

            npo_impact = NPOMetrics(
                features_shipped=metrics.npo_features_closed,
                avg_time_to_deliver=avg_npo_time,
            )

            alerts = AlertMetrics(
                stale_prs=metrics.alerts_stale_prs,
                stale_issues=metrics.alerts_stale_issues,
            )

            reports.append(
                TeamReport(
                    team_name=team_name,
                    velocity=velocity,
                    participation=participation,
                    npo_impact=npo_impact,
                    alerts=alerts,
                    start_date=one_week_ago.date().isoformat(),
                    end_date=now.date().isoformat(),
                )
            )

        return reports
