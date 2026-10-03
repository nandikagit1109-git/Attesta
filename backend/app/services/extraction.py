"""Text extraction: pdfplumber for text PDFs, pytesseract for images when a
Tesseract binary is configured. Returns (text, warnings)."""

import logging

from ..config import get_settings

logger = logging.getLogger("attesta.extraction")


def extract_text(path: str, mime_type: str) -> tuple[str, list[str]]:
    settings = get_settings()
    warnings: list[str] = []

    if "pdf" in (mime_type or "") or path.lower().endswith(".pdf"):
        try:
            import pdfplumber
        except ImportError:
            warnings.append("pdfplumber-not-installed")
            return "", warnings

        try:
            pages = []
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages[:10]:  # certificates are short; cap anyway
                    pages.append(page.extract_text() or "")
            text = "\n".join(pages).strip()
        except Exception as exc:
            logger.warning("pdf extraction failed: %s", exc)
            warnings.append("pdf-extraction-failed")
            return "", warnings

        if not text:
            warnings.append("no-embedded-text")
        return text, warnings

    if any(ext in (mime_type or "") for ext in ("image",)) or path.lower().endswith((".png", ".jpg", ".jpeg")):
        if not settings.tesseract_cmd:
            warnings.append("ocr-not-configured")
            return "", warnings
        try:
            import pytesseract
            from PIL import Image

            pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd
            text = pytesseract.image_to_string(Image.open(path))
            return text.strip(), warnings
        except Exception as exc:
            logger.warning("ocr failed: %s", exc)
            warnings.append("ocr-failed")
            return "", warnings

    warnings.append("unsupported-for-extraction")
    return "", warnings
