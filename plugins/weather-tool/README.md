# Weather Tool Plugin

Simple weather data fetching plugin for BAEL.

## Installation

1. Copy this directory to your BAEL `plugins/` folder
2. Get an API key from [OpenWeatherMap](https://openweathermap.org/api)
3. Configure the plugin with your API key

## Configuration

```yaml
api_key: "your_api_key_here"
units: metric # or imperial
timeout: 10
```

## Usage

```python
from core.plugins.registry import PluginRegistry

registry = PluginRegistry(Path("plugins"))
await registry.load_plugin(
    "weather-tool",
    config={"api_key": "your_key"}
)

plugin = registry.get_plugin("weather-tool")
weather = await plugin.get_weather("London")
print(f"Temperature: {weather['temperature']}°C")
```

## API

### `get_weather(city: str) -> Dict[str, Any]`

Fetches current weather for a city.

**Returns:**

```python
{
    "city": "London",
    "country": "GB",
    "temperature": 15.5,
    "feels_like": 14.2,
    "humidity": 72,
    "pressure": 1013,
    "description": "light rain",
    "wind_speed": 4.5,
    "units": "metric"
}
```
