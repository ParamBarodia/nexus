"""India MCP: ESPNCricInfo Score stub."""
def get_service():
    return {
        "name": "espncricinfo",
        "description": "Get live cricket scores.",
        "parameters": {
            "type": "object",
            "properties": {"match_id": {"type": "string", "description": "Optional match identifier"}},
        },
        "handler": lambda match_id="live": f"Current Score: India 245/3 (35.2 ov) - (Stub)."
    }
