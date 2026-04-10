"""India MCP: UPI Status stub."""
def get_service():
    return {
        "name": "upi_status",
        "description": "Check status of UPI payment (mock/India-specific).",
        "parameters": {
            "type": "object",
            "properties": {"txn_id": {"type": "string"}},
            "required": ["txn_id"]
        },
        "handler": lambda txn_id: f"Transaction {txn_id} is SUCCESSFUL (Stub)."
    }
