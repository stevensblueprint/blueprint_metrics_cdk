import os
from typing import Sequence

from google.auth import aws as google_auth_aws
from google.auth.transport.requests import Request


def google_creds_from_env(scopes: Sequence[str]):
    audience = os.environ["GOOGLE_WORKLOADIDENTITY_AUDIENCE"]
    service_account = os.environ["GOOGLE_WORKLOADIDENTITY_SERVICEACCOUNT"]
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
    if not region:
        raise RuntimeError("AWS_DEFAULT_REGION (or AWS_REGION) must be set")

    info = {
        "type": "external_account",
        "audience": audience,
        "subject_token_type": "urn:ietf:params:aws:token-type:aws4_request",
        "token_url": "https://sts.googleapis.com/v1/token",
        # The AWS "credential_source" for Lambda: use regional GetCallerIdentity URL.
        "credential_source": {
            "environment_id": "aws1",
            "regional_cred_verification_url": (
                f"https://sts.{region}.amazonaws.com"
                "?Action=GetCallerIdentity&Version=2011-06-15"
            ),
        },
        # Service account impersonation (generate short-lived access tokens):
        "service_account_impersonation_url": (
            "https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/"
            f"{service_account}:generateAccessToken"
        ),
    }

    creds = google_auth_aws.Credentials.from_info(info, scopes=list(scopes))
    creds.refresh(Request())
    return creds
