import os
import logging
from dotenv import load_dotenv
from app.agents.api_integration_agent import APIConnectorConfig, AuthMethod, APIIntegrationError
from app.agents.rest_connector import RESTConnector

load_dotenv()
logger = logging.getLogger(__name__)


async def get_country_info(country_name: str) -> dict:
    """
    Fetch business-relevant country data using RestCountries API.
    Connector config loaded from CONNECTOR_COUNTRIES_* env vars.
    """
    def _make_connector():
        config = APIConnectorConfig.from_env("CONNECTOR_COUNTRIES")
        return RESTConnector(config)

    connector = _make_connector()

    validation = connector.validate_config()
    if not validation["valid"]:
        return {
            "success": False,
            "output": f"Countries connector not configured: {validation['issues']}",
            "data": {},
        }

    try:
        result = await connector.get(f"/name/{country_name}")
        raw = result.get("data", [])

        if not raw or not isinstance(raw, list):
            return {
                "success": False,
                "output": f"No data found for country: {country_name}",
                "data": {},
            }

        country = raw[0]
        name = country.get("name", {}).get("common", country_name)
        capital = country.get("capital", ["N/A"])[0] if country.get("capital") else "N/A"
        population = country.get("population", "N/A")
        region = country.get("region", "N/A")
        currencies = country.get("currencies", {})
        currency_names = ", ".join(
            v.get("name", k) for k, v in currencies.items()
        ) if currencies else "N/A"
        languages = country.get("languages", {})
        language_list = ", ".join(languages.values()) if languages else "N/A"

        output = (
            f"{name}: Capital: {capital}. "
            f"Population: {population:,}. "
            f"Region: {region}. "
            f"Currency: {currency_names}. "
            f"Languages: {language_list}."
        )

        return {"success": True, "output": output, "data": country}

    except APIIntegrationError as e:
        logger.error(f"Countries connector error: {e}")
        return {"success": False, "output": str(e), "data": {}}