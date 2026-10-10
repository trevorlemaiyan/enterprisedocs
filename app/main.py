import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.config import Settings, get_settings
from app.embeddings.provider import EmbeddingConfigError, EmbeddingError
from app.llm.provider import LLMConfigError, LLMError
from app.rag.service import RagService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("enterprisedocs")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = RagService(settings)
        if settings.auto_ingest:
            report = app.state.service.ingest()
            logger.info(
                "Ingest: %d added, %d updated, %d unchanged, %d removed, %d failed",
                len(report.added), len(report.updated), len(report.unchanged),
                len(report.removed), len(report.failed),
            )
        yield

    app = FastAPI(
        title="EnterpriseDocs AI",
        description="Ask questions about company documents and get answers with citations (RAG).",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.include_router(router)

    # Clients get a short, safe message. Details go to the log, never into the response.
    def _handler(status: int, message: str):
        async def handle(_: Request, exc: Exception) -> JSONResponse:
            logger.error("%s: %s", type(exc).__name__, exc)
            return JSONResponse(status_code=status, content={"detail": message})
        return handle

    app.add_exception_handler(LLMConfigError, _handler(503, "The language model is not configured."))
    app.add_exception_handler(LLMError, _handler(502, "The language model service failed."))
    app.add_exception_handler(EmbeddingConfigError, _handler(503, "The embedding service is not configured."))
    app.add_exception_handler(EmbeddingError, _handler(502, "The embedding service failed."))
    return app


app = create_app()
