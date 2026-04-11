"""Screenshot capture with OCR text extraction."""


def _screenshot_ocr(region: str = "") -> str:
    """Capture a screenshot and extract text via OCR.

    Args:
        region: Optional comma-separated "left,top,right,bottom" pixel coords.
                If empty, captures the full primary screen.
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        return "Error: Pillow is not installed. Run: pip install Pillow"

    try:
        import pytesseract
    except ImportError:
        return "Error: pytesseract is not installed. Run: pip install pytesseract"

    try:
        bbox = None
        if region:
            parts = [int(x.strip()) for x in region.split(",")]
            if len(parts) == 4:
                bbox = tuple(parts)

        img = ImageGrab.grab(bbox=bbox)
        text = pytesseract.image_to_string(img)
        return text.strip() if text.strip() else "(No text detected in screenshot)"
    except Exception as e:
        return f"Screenshot OCR failed: {e}"


def get_tools() -> list:
    return [
        {
            "name": "screenshot_ocr",
            "description": "Capture a screenshot of the screen (or a region) and extract text using OCR.",
            "parameters": {
                "type": "object",
                "properties": {
                    "region": {
                        "type": "string",
                        "description": "Optional bounding box as 'left,top,right,bottom' pixels. Empty for full screen."
                    }
                },
                "required": []
            },
            "handler": _screenshot_ocr
        }
    ]
