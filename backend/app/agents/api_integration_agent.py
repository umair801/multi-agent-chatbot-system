import os
import logging
import base64
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class AuthMethod(str, Enum):
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    NONE = "none"


@dataclass
class APIConnectorConfig:
    """
    Configuration schema for an external API connector.
    All values loaded from environment variables — no hardcoding.
    """
    name: str
    base_url: str
    auth_method: AuthMethod
    auth_token: Optional[str] = None
    auth_username: Optional[str] = None
    auth_password: Optional[str] = None
    api_key_header: str = "X-API-Key"
    timeout: int = 10
    extra_headers: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, prefix: str) -> "APIConnectorConfig":
        """
        Load connector config from environment variables using a prefix.

        Example prefix: CONNECTOR_CRM
        Expects env vars:
          CONNECTOR_CRM_NAME
          CONNECTOR_CRM_BASE_URL
          CONNECTOR_CRM_AUTH_METHOD   (bearer | api_key | basic | none)
          CONNECTOR_CRM_AUTH_TOKEN    (for bearer or api_key)
          CONNECTOR_CRM_AUTH_USERNAME (for basic)
          CONNECTOR_CRM_AUTH_PASSWORD (for basic)
          CONNECTOR_CRM_API_KEY_HEADER (optional, defaults to X-API-Key)
          CONNECTOR_CRM_TIMEOUT       (optional, defaults to 10)
        """
        p = prefix.upper()
        return cls(
            name=os.getenv(f"{p}_NAME", prefix),
            base_url=os.getenv(f"{p}_BASE_URL", ""),
            auth_method=AuthMethod(os.getenv(f"{p}_AUTH_METHOD", "none").lower()),
            auth_token=os.getenv(f"{p}_AUTH_TOKEN"),
            auth_username=os.getenv(f"{p}_AUTH_USERNAME"),
            auth_password=os.getenv(f"{p}_AUTH_PASSWORD"),
            api_key_header=os.getenv(f"{p}_API_KEY_HEADER", "X-API-Key"),
            timeout=int(os.getenv(f"{p}_TIMEOUT", "10")),
        )


class APIIntegrationError(Exception):
    """Raised when an external API call fails."""
    def __init__(self, connector_name: str, message: str, status_code: Optional[int] = None):
        self.connector_name = connector_name
        self.status_code = status_code
        super().__init__(f"[{connector_name}] {message} (status={status_code})")


class BaseAPIConnector:
    """
    Base class for all external API connectors.
    Subclasses implement their specific endpoint calls.
    Auth headers, error handling, and logging are handled here.
    """

    def __init__(self, config: APIConnectorConfig):
        self.config = config
        logger.info(f"Initialized connector: {config.name} -> {config.base_url}")

    def _build_headers(self) -> dict:
        """Build auth headers based on configured auth method."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        headers.update(self.config.extra_headers)

        method = self.config.auth_method

        if method == AuthMethod.BEARER:
            token = self.config.auth_token
            if not token:
                raise APIIntegrationError(self.config.name, "Bearer token not set")
            headers["Authorization"] = f"Bearer {token}"

        elif method == AuthMethod.API_KEY:
            token = self.config.auth_token
            if not token:
                raise APIIntegrationError(self.config.name, "API key not set")
            headers[self.config.api_key_header] = token

        elif method == AuthMethod.BASIC:
            username = self.config.auth_username or ""
            password = self.config.auth_password or ""
            if not username:
                raise APIIntegrationError(self.config.name, "Basic auth username not set")
            credentials = base64.b64encode(
                f"{username}:{password}".encode()
            ).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    def _handle_response_error(self, status_code: int, body: str) -> None:
        """Raise structured error for non-2xx responses."""
        if status_code >= 400:
            raise APIIntegrationError(
                self.config.name,
                f"Request failed: {body[:200]}",
                status_code=status_code,
            )

    def validate_config(self) -> dict:
        """
        Validate required config fields are present.
        Returns dict with validation result.
        """
        issues = []

        if not self.config.base_url:
            issues.append("base_url is not set")

        if self.config.auth_method in (AuthMethod.BEARER, AuthMethod.API_KEY):
            if not self.config.auth_token:
                issues.append(f"auth_token required for {self.config.auth_method} auth")

        if self.config.auth_method == AuthMethod.BASIC:
            if not self.config.auth_username:
                issues.append("auth_username required for basic auth")

        if issues:
            logger.warning(f"[{self.config.name}] Config issues: {issues}")
            return {"valid": False, "issues": issues}

        return {"valid": True, "issues": []}