"""India MCP: WhatsApp Send stub."""
def get_service():
    return {
        "name": "whatsapp_send",
        "description": "Stub for sending WhatsApp messages via future Baileys integration.",
        "parameters": {
            "type": "object",
            "properties": {
                "number": {"type": "string"},
                "message": {"type": "string"}
            },
            "required": ["number", "message"]
        },
        "handler": lambda number, message: f"Message queued for {number}: {message} (Stub)."
    }
