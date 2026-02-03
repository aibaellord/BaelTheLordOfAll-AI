"""
Weather Tool Plugin for BAEL
Fetches current weather data using OpenWeatherMap API.
"""

import logging
from typing import Any, Dict, Optional

import requests

from core.plugins.registry import PluginInterface, PluginManifest

logger = logging.getLogger("BAEL.Plugin.Weather")


class WeatherTool(PluginInterface):
    """Weather data fetching tool."""

    def __init__(self, manifest: PluginManifest, config: Dict[str, Any]):
        super().__init__(manifest, config)
        self.api_key = config.get("api_key")
        self.units = config.get("units", "metric")
        self.timeout = config.get("timeout", 10)
        self.base_url = "https://api.openweathermap.org/data/2.5/weather"

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        if not self.api_key:
            self.logger.error("API key not provided in configuration")
            return False

        self.logger.info("✅ Weather tool initialized")
        return True

    async def get_weather(self, city: str) -> Dict[str, Any]:
        """
        Get current weather for a city.

        Args:
            city: City name (e.g., "London", "New York")

        Returns:
            Weather data dictionary
        """
        try:
            params = {
                "q": city,
                "appid": self.api_key,
                "units": self.units
            }

            response = requests.get(
                self.base_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()

            # Extract relevant information
            result = {
                "city": data["name"],
                "country": data["sys"]["country"],
                "temperature": data["main"]["temp"],
                "feels_like": data["main"]["feels_like"],
                "humidity": data["main"]["humidity"],
                "pressure": data["main"]["pressure"],
                "description": data["weather"][0]["description"],
                "wind_speed": data["wind"]["speed"],
                "units": self.units
            }

            self.logger.info(f"Weather fetched for {city}: {result['temperature']}°")
            return result

        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch weather for {city}: {e}")
            return {"error": str(e)}

    async def shutdown(self):
        """Cleanup resources."""
        self.logger.info("Weather tool shutdown")


def register(manifest: PluginManifest, config: Dict[str, Any]) -> WeatherTool:
    """
    Plugin entry point.

    Args:
        manifest: Plugin manifest
        config: Plugin configuration

    Returns:
        WeatherTool instance
    """
    return WeatherTool(manifest, config)
