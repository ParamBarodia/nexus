"""India MCP: IRCTC Train Status stub."""
def get_service():
    return {
        "name": "irctc_train",
        "description": "Check Indian train status by number.",
        "parameters": {
            "type": "object",
            "properties": {"train_no": {"type": "string"}},
            "required": ["train_no"]
        },
        "handler": lambda train_no: f"Train {train_no} is currently ON TIME (Stub)."
    }
