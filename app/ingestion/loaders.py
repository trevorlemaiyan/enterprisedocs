"""Read PDF / text / Markdown files into per-page text."""

import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class DocumentError(Exception):
    """A document could not be read. The message is safe to show to API clients."""


@dataclass(frozen=True)
class Page:
    number: int  # 1-based
    text: str


def load_document(path: Path) -> list[Page]:
    extension = path.suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise DocumentError(f"Unsupported file type '{extension}'. Supported types: {allowed}.")

    pages = _load_pdf(path) if extension == ".pdf" else [Page(1, _read_text(path))]
    pages = _strip_repeated_lines(pages)

    if not any(page.text.strip() for page in pages):
        raise DocumentError(
            "The document has no extractable text (scanned PDFs need OCR, which is not supported)."
        )
    return pages


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise DocumentError("The file could not be read.") from exc


def _load_pdf(path: Path) -> list[Page]:
    from pypdf import PdfReader  # imported lazily: only needed for PDFs

    try:
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise DocumentError("Encrypted PDFs are not supported.")
        return [Page(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]
    except DocumentError:
        raise
    except Exception as exc:  # pypdf raises many different error types for broken files
        raise DocumentError("The PDF could not be read; it may be corrupt.") from exc


def _line_key(line: str) -> str:
    # "Page 1" and "Page 2" must count as the same repeated line.
    return re.sub(r"\d+", "#", line.strip().lower())


def _strip_repeated_lines(pages: list[Page]) -> list[Page]:
    """Remove running headers/footers (lines that repeat on most pages) so they don't pollute chunks."""
    if len(pages) < 2:
        return pages

    counts: Counter[str] = Counter()
    for page in pages:
        counts.update({_line_key(line) for line in page.text.splitlines() if line.strip()})

    threshold = max(2, math.ceil(0.6 * len(pages)))
    repeated = {key for key, count in counts.items() if count >= threshold and len(key) <= 120}

    return [
        Page(page.number, "\n".join(l for l in page.text.splitlines() if _line_key(l) not in repeated))
        for page in pages
    ]
