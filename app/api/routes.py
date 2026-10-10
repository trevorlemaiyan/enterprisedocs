from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse

from app.api.schemas import (
    AskRequest, AskResponse, DeleteDocumentResponse, DocumentOut, IngestResponse,
    SearchRequest, SearchResponse, SearchResultOut, SourceOut, UploadResponse,
)
from app.api.ui import INDEX_HTML
from app.domain import Hit
from app.ingestion.loaders import DocumentError
from app.rag.service import RagService, UploadError

router = APIRouter()

SNIPPET_CHARS = 300


def get_service(request: Request) -> RagService:
    return request.app.state.service


def _snippet(text: str) -> str:
    return text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "..."


def _source(number: int, hit: Hit) -> SourceOut:
    return SourceOut(
        id=number, document=hit.chunk.document, page=hit.chunk.page, section=hit.chunk.section,
        snippet=_snippet(hit.chunk.text), score=round(hit.score, 4),
    )


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index() -> HTMLResponse:
    """Serve the interactive web interface."""
    return HTMLResponse(content=INDEX_HTML)


@router.get("/health")
def health(request: Request) -> dict:
    service = get_service(request)
    return {"status": "ok", "documents": len(service.documents()), "chunks": len(service.store)}


@router.post("/ask", response_model=AskResponse)
def ask(body: AskRequest, request: Request) -> AskResponse:
    result = get_service(request).ask(body.question, body.top_k)
    return AskResponse(
        answer=result.answer,
        grounded=result.grounded,
        sources=[_source(number, hit) for number, hit in result.sources],
    )


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest, request: Request) -> SearchResponse:
    """Retrieval only, with no LLM. Useful for seeing exactly what the model would be given."""
    service = get_service(request)
    hits = service.search(body.query, body.top_k)
    return SearchResponse(
        min_score=service.min_score,
        results=[
            SearchResultOut(**_source(i, hit).model_dump(), relevant=hit.score >= service.min_score)
            for i, hit in enumerate(hits, start=1)
        ],
    )


@router.get("/documents", response_model=list[DocumentOut])
def list_documents(request: Request) -> list[DocumentOut]:
    documents = get_service(request).documents()
    return [
        DocumentOut(name=name, pages=info["pages"], chunks=info["chunks"], sha256=info["sha256"])
        for name, info in sorted(documents.items())
    ]


@router.post("/documents", response_model=UploadResponse, status_code=201)
def upload_document(request: Request, file: UploadFile = File(...)) -> UploadResponse:
    service = get_service(request)
    limit = service.settings.max_upload_mb * 1024 * 1024
    data = file.file.read(limit + 1)  # never read more than one byte past the limit into memory
    try:
        name = service.add_upload(file.filename or "", data)
    except UploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except DocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return UploadResponse(document=name, chunks=service.documents()[name]["chunks"])


@router.delete("/documents/{name}", response_model=DeleteDocumentResponse)
def delete_document(name: str, request: Request) -> DeleteDocumentResponse:
    service = get_service(request)
    deleted = service.delete_document(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document '{name}' not found.")
    return DeleteDocumentResponse(document=name, deleted=True)


@router.post("/ingest", response_model=IngestResponse)
def ingest(request: Request, force: bool = False) -> IngestResponse:
    """Re-scan the documents folder. Unchanged files are skipped unless force=true."""
    report = get_service(request).ingest(force=force)
    return IngestResponse(**report.__dict__)
