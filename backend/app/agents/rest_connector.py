import os
import logging
from typing import Any, Optional
import httpx
from dotenv import load_dotenv
from app.agents.api_integration_agent import (
    BaseAPIConnector,
    APIConnectorConfig,
    APIIntegrationError,
)

load_dotenv()
logger = logging.getLogger(__name__)


class RESTConnector(BaseAPIConnector):
    """
    Generic REST connector supporting GET and POST with all auth methods.
    All API clients are initialized inside methods — never at module level.
    """

    async def get(
        self,
        endpoint: str,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Perform an authenticated GET request.

        Args:
            endpoint: Path appended to base_url (e.g. '/users')
            params:   Optional query parameters

        Returns:
            dict with keys: success, status_code, data, connector
        """
        validation = self.validate_config()
        if not validation["valid"]:
            raise APIIntegrationError(
                self.config.name,
                f"Invalid config: {validation['issues']}",
            )

        url = f"{self.config.base_url.rstrip('/')}{endpoint}"
        headers = self._build_headers()

        logger.info(f"[{self.config.name}] GET {url} params={params}")

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params or {})
                self._handle_response_error(response.status_code, response.text)

                try:
                    data = response.json()
                except Exception:
                    data = {"raw": response.text}

                logger.info(f"[{self.config.name}] GET {url} -> {response.status_code}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "connector": self.config.name,
                }

            except APIIntegrationError:
                raise
            except httpx.TimeoutException:
                raise APIIntegrationError(
                    self.config.name,
                    f"Request timed out after {self.config.timeout}s",
                )
            except httpx.ConnectError:
                raise APIIntegrationError(
                    self.config.name,
                    f"Could not connect to {url}",
                )
            except Exception as e:
                raise APIIntegrationError(
                    self.config.name,
                    f"Unexpected error: {str(e)}",
                )

    async def post(
        self,
        endpoint: str,
        payload: Optional[dict] = None,
        params: Optional[dict] = None,
    ) -> dict:
        """
        Perform an authenticated POST request.

        Args:
            endpoint: Path appended to base_url (e.g. '/tasks')
            payload:  JSON body as dict
            params:   Optional query parameters

        Returns:
            dict with keys: success, status_code, data, connector
        """
        validation = self.validate_config()
        if not validation["valid"]:
            raise APIIntegrationError(
                self.config.name,
                f"Invalid config: {validation['issues']}",
            )

        url = f"{self.config.base_url.rstrip('/')}{endpoint}"
        headers = self._build_headers()

        logger.info(f"[{self.config.name}] POST {url} payload={payload}")

        async with httpx.AsyncClient(timeout=self.config.timeout) as client:
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload or {},
                    params=params or {},
                )
                self._handle_response_error(response.status_code, response.text)

                try:
                    data = response.json()
                except Exception:
                    data = {"raw": response.text}

                logger.info(f"[{self.config.name}] POST {url} -> {response.status_code}")
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "data": data,
                    "connector": self.config.name,
                }

            except APIIntegrationError:
                raise
            except httpx.TimeoutException:
                raise APIIntegrationError(
                    self.config.name,
                    f"Request timed out after {self.config.timeout}s",
                )
            except httpx.ConnectError:
                raise APIIntegrationError(
                    self.config.name,
                    f"Could not connect to {url}",
                )
            except Exception as e:
                raise APIIntegrationError(
                    self.config.name,
                    f"Unexpected error: {str(e)}",
                )