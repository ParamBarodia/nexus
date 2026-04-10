"""India MCP: IMD Weather stub."""
def get_service():
    return {
        "name": "imd_weather",
        "description": "Get weather update from IMD for Indian cities.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"]
        },
        "handler": lambda city: f"Weather in {city}: 32°C, Sunny (Stub)."
    }
