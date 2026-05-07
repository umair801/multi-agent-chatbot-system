import os
import logging
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


async def get_weather(city: str) -> dict:
    """
    Fetch current weather for a city using wttr.in (no API key required).
    Falls back gracefully if the request fails.
    """
    url = f"https://wttr.in/{city}?format=j1"
    headers = {"User-Agent": "Datawebify-AgAI24/1.0"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()

        current = data.get("current_condition", [{}])[0]
        temp_c = current.get("temp_C", "N/A")
        feels_like = current.get("FeelsLikeC", "N/A")
        humidity = current.get("humidity", "N/A")
        description = current.get("weatherDesc", [{}])[0].get("value", "N/A")
        wind_kmph = current.get("windspeedKmph", "N/A")

        nearest = data.get("nearest_area", [{}])[0]
        area = nearest.get("areaName", [{}])[0].get("value", city)
        country = nearest.get("country", [{}])[0].get("value", "")

        output = (
            f"Weather in {area}, {country}: {description}. "
            f"Temperature: {temp_c}C, feels like {feels_like}C. "
            f"Humidity: {humidity}%. Wind: {wind_kmph} km/h."
        )

        logger.info(f"Weather fetched for {city}: {output}")
        return {"success": True, "output": output, "data": current}

    except Exception as e:
        logger.error(f"Weather connector error: {e}")
        return {"success": False, "output": str(e), "data": {}}
