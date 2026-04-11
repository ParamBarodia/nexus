"""Read text content from PDF files."""

import json


def _pdf_read(file_path: str = "", pages: str = "") -> str:
    """Extract text from a PDF file.

    Args:
        file_path: Absolute path to the PDF file.
        pages: Optional page range, e.g. '1-5', '3', '1,3,5'. Empty for all pages.
    """
    if not file_path:
        return "Error: 'file_path' parameter is required."

    import os
    if not os.path.isfile(file_path):
        return f"Error: file not found: {file_path}"

    try:
        import pdfplumber
    except ImportError:
        return "Error: pdfplumber is not installed. Run: pip install pdfplumber"

    try:
        page_indices = _parse_pages(pages)

        with pdfplumber.open(file_path) as pdf:
            total = len(pdf.pages)
            results = []

            if page_indices:
                targets = [i for i in page_indices if 0 <= i < total]
            else:
                targets = range(total)

            for i in targets:
                page = pdf.pages[i]
                text = page.extract_text() or ""
                results.append({"page": i + 1, "text": text})

            return json.dumps({
                "file": file_path,
                "total_pages": total,
                "extracted_pages": len(results),
                "pages": results
            }, indent=2)
    except Exception as e:
        return f"PDF read failed: {e}"


def _parse_pages(pages_str: str) -> list[int] | None:
    """Parse a pages string like '1-5', '3', '1,3,5' into zero-based indices."""
    if not pages_str:
        return None

    indices = []
    for part in pages_str.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            for p in range(int(start), int(end) + 1):
                indices.append(p - 1)
        else:
            indices.append(int(part) - 1)
    return indices


def get_tools() -> list:
    return [
        {
            "name": "pdf_read",
            "description": "Extract text content from a PDF file, optionally limited to specific pages.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the PDF file."
                    },
                    "pages": {
                        "type": "string",
                        "description": "Optional page range: '1-5', '3', '1,3,5'. Empty for all pages."
                    }
                },
                "required": ["file_path"]
            },
            "handler": _pdf_read
        }
    ]
