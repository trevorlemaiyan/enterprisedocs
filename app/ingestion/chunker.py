"""Heading-aware chunking.

Chunks never cross a section heading, so every chunk can be cited as "document, page, section".
Sections longer than `size` characters are split on sentence boundaries, with `overlap`
characters repeated at the start of the next chunk so facts at a boundary are not cut in half.
"""

import re
from bisect import bisect_right
from dataclasses import dataclass

from app.ingestion.loaders import Page

# "2. Annual Leave", "4.1 Entitlement", "3) Probation"
_NUMBERED_HEADING = re.compile(r"^\s*\d{1,2}(?:\.\d{1,2})*[.)]?\s+[A-Z][^.!?:;]{2,80}$")
# "## Annual Leave"
_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+(.+?)\s*#*\s*$")
_SENTENCE_BREAK = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class TextChunk:
    text: str
    page: int
    section: str


def _heading(line: str) -> str | None:
    if _NUMBERED_HEADING.match(line):
        return line.strip()
    if match := _MARKDOWN_HEADING.match(line):
        return match.group(1)
    return None


def chunk_pages(
    pages: list[Page], default_section: str, size: int = 900, overlap: int = 150
) -> list[TextChunk]:
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("chunk size must be positive and larger than the overlap")

    chunks: list[TextChunk] = []
    lines: list[tuple[int, str]] = []
    section = default_section

    def flush() -> None:
        if lines:
            chunks.extend(_split_section(lines, section, size, overlap))
            lines.clear()

    for page in pages:
        for raw in page.text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if (label := _heading(line)) is not None:
                flush()
                section = label
                continue
            lines.append((page.number, line))
    flush()
    return chunks


def _split_section(
    lines: list[tuple[int, str]], section: str, size: int, overlap: int
) -> list[TextChunk]:
    # Join the section's lines into one string, remembering which page each line came from.
    offsets: list[int] = []
    pages: list[int] = []
    parts: list[str] = []
    position = 0
    for page_number, line in lines:
        if parts:
            position += 1  # the joining space
        offsets.append(position)
        pages.append(page_number)
        parts.append(line)
        position += len(line)
    text = " ".join(parts)

    def page_at(offset: int) -> int:
        return pages[bisect_right(offsets, offset) - 1]

    if len(text) <= size:
        return [TextChunk(text, page_at(0), section)]

    spans = _fit_spans(_sentence_spans(text), text, size)
    chunks: list[TextChunk] = []
    i = 0
    while i < len(spans):
        j = i + 1
        while j < len(spans) and spans[j][1] - spans[i][0] <= size:
            j += 1
        chunks.append(TextChunk(text[spans[i][0] : spans[j - 1][1]], page_at(spans[i][0]), section))
        if j >= len(spans):
            break
        # Step back over whole sentences to build the overlap, but always move forward.
        k = j
        while k - 1 > i and spans[j - 1][1] - spans[k - 1][0] <= overlap:
            k -= 1
        i = k
    return chunks


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in _SENTENCE_BREAK.finditer(text):
        spans.append((start, match.start()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans


def _fit_spans(spans: list[tuple[int, int]], text: str, size: int) -> list[tuple[int, int]]:
    """Split any single sentence longer than `size` on word boundaries."""
    fitted: list[tuple[int, int]] = []
    for start, end in spans:
        if end - start <= size:
            fitted.append((start, end))
            continue
        piece_start = start
        for word in re.finditer(r"\S+", text[start:end]):
            word_end = start + word.end()
            if word_end - piece_start > size and start + word.start() > piece_start:
                fitted.append((piece_start, start + word.start() - 1))
                piece_start = start + word.start()
        fitted.append((piece_start, end))
    return fitted
