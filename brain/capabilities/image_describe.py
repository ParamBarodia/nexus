"""Describe image content using a local vision model (Ollama + llava)."""

import json


def _image_describe(file_path: str = "", prompt: str = "Describe this image in detail.") -> str:
    """Describe the contents of an image using a local vision model.

    Args:
        file_path: Absolute path to the image file.
        prompt: Custom prompt for the vision model (default: 'Describe this image in detail.').
    """
    if not file_path:
        return "Error: 'file_path' parameter is required."

    import os
    if not os.path.isfile(file_path):
        return f"Error: file not found: {file_path}"

    prompt = prompt or "Describe this image in detail."

    # Try Ollama with llava model
    try:
        import base64
        import subprocess

        with open(file_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        # Use Ollama REST API (localhost:11434)
        try:
            import requests
            payload = {
                "model": "llava",
                "prompt": prompt,
                "images": [img_b64],
                "stream": False
            }
            resp = requests.post("http://localhost:11434/api/generate", json=payload, timeout=120)
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps({
                    "file": file_path,
                    "model": "llava",
                    "description": data.get("response", "").strip()
                }, indent=2)
        except ImportError:
            # No requests library, try subprocess with curl
            pass

        # Fallback: use subprocess + curl
        curl_payload = json.dumps({
            "model": "llava",
            "prompt": prompt,
            "images": [img_b64],
            "stream": False
        })
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", "http://localhost:11434/api/generate",
             "-H", "Content-Type: application/json", "-d", "@-"],
            input=curl_payload, capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return json.dumps({
                "file": file_path,
                "model": "llava",
                "description": data.get("response", "").strip()
            }, indent=2)

    except Exception:
        pass

    return json.dumps({
        "file": file_path,
        "model": None,
        "description": "Image description not available. Ensure Ollama is running with the llava model: ollama pull llava && ollama serve"
    }, indent=2)


def get_tools() -> list:
    return [
        {
            "name": "image_describe",
            "description": "Describe the contents of an image using a local vision model (Ollama llava).",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the image file."
                    },
                    "prompt": {
                        "type": "string",
                        "description": "Custom prompt for the vision model (default: 'Describe this image in detail.')."
                    }
                },
                "required": ["file_path"]
            },
            "handler": _image_describe
        }
    ]
