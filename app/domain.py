"""Plain data types shared by the ingestion, storage and answering layers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str  # e.g. "Leave_Policy-004"
    document: str  # file name, shown in citations
    page: int  # 1-based page where the chunk starts
    section: str  # nearest heading above the chunk
    text: str
    ordinal: int  # position within the document


@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float  # cosine similarity, higher is better
