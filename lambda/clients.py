from typing import Sequence, Optional, Any
from google.auth import aws as google_auth_aws
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials
from googleapiclient.discovery import build
import logging
from github import Github
import threading
from utils import safe_get_env
import boto3

logger = logging.getLogger(__name__)


class GithubClient:
    _instance: Optional["GithubClient"] = None
    _client: Optional[Github] = None

    def __new__(cls) -> "GithubClient":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._initialize()
            cls._instance = instance
        return cls._instance

    def _initialize(self) -> None:
        logger.info("Initializing GithubClient...")
        token = safe_get_env("GITHUB_TOKEN")
        if not token:
            logger.warning("GITHUB_TOKEN environment variable not set.")
        self._client = Github(token)
        logger.info("GithubClient initialized successfully.")

    @property
    def client(self) -> Github:
        if self._client is None:
            raise RuntimeError("GithubClient not initialized.")
        return self._client


class SheetsClient:
    _instance: Optional["SheetsClient"] = None
    _local = threading.local()

    SCOPES: Sequence[str] = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    ]

    def __new__(cls) -> "SheetsClient":
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._creds = None
            instance._initialize()
            cls._instance = instance
        return cls._instance

    def _initialize(self) -> None:
        logger.info("Initializing SheetsClient...")
        self._creds = self._google_creds_from_env()
        logger.info("SheetsClient initialized successfully.")

    def _google_creds_from_env(self) -> Credentials:
        """
        Create Google credentials using AWS → Google Workload Identity Federation.
        """
        audience = safe_get_env("GOOGLE_WORKLOADIDENTITY_AUDIENCE")
        service_account = safe_get_env("GOOGLE_WORKLOADIDENTITY_SERVICEACCOUNT")
        region = safe_get_env("AWS_REGION") or safe_get_env("AWS_DEFAULT_REGION")

        if not region:
            raise RuntimeError("AWS_REGION or AWS_DEFAULT_REGION must be set")

        try:
            sts = boto3.client("sts", region_name=region)
            caller_identity = sts.get_caller_identity()
            logger.info(f"AWS Caller Identity: {caller_identity['Arn']}")
        except Exception as e:
            logger.warning(f"Could not determine AWS Caller Identity: {e}")

        logger.info(f"Using Google WIF Audience: {audience}")
        logger.info(f"Using Google Service Account: {service_account}")

        info = {
            "type": "external_account",
            "audience": audience,
            "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
            "token_url": "https://sts.googleapis.com/v1/token",
            "credential_source": {
                "environment_id": "aws1",
                "regional_cred_verification_url": (
                    f"https://sts.{region}.amazonaws.com"
                    "?Action=GetCallerIdentity&Version=2011-06-15"
                ),
            },
            "service_account_impersonation_url": (
                "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
                f"{service_account}:generateAccessToken"
            ),
        }

        creds = google_auth_aws.Credentials.from_info(
            info,
            scopes=list(self.SCOPES),
        )
        creds.refresh(Request())
        logging.info(
            "Access token starts with: %s", creds.token[:10] if creds.token else "None"
        )
        return creds

    def _get_thread_service(self) -> Any:
        svc = getattr(self._local, "service", None)
        if svc is None:
            svc = build(
                "sheets",
                "v4",
                credentials=self._creds,
                cache_discovery=False,
            )
            self._local.service = svc
        return svc

    def get_values(self, spreadsheet_id: str, a1_range: str) -> list[list[str]]:
        service = self._get_thread_service()
        resp = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=a1_range,
            )
            .execute(num_retries=5)
        )
        return resp.get("values", [])
