from pydantic import BaseModel, Field


class SourceOut(BaseModel):
    id: int = Field(description="Citation number, matching [n] in the answer")
    document: str
    page: int
    section: str
    snippet: str
    score: float


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class AskResponse(BaseModel):
    answer: str
    grounded: bool = Field(description="True if the answer cites at least one retrieved passage")
    sources: list[SourceOut]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=10)


class SearchResultOut(SourceOut):
    relevant: bool = Field(description="Score is at or above the relevance threshold")


class SearchResponse(BaseModel):
    min_score: float
    results: list[SearchResultOut]


class DocumentOut(BaseModel):
    name: str
    pages: int
    chunks: int
    sha256: str


class IngestResponse(BaseModel):
    added: list[str]
    updated: list[str]
    unchanged: list[str]
    removed: list[str]
    failed: dict[str, str]


class UploadResponse(BaseModel):
    document: str
    chunks: int


class DeleteDocumentResponse(BaseModel):
    document: str
    deleted: bool
