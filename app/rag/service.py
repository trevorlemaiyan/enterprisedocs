"""RagService: ingestion, search and question answering behind one object."""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.domain import Chunk, Hit
from app.embeddings.provider import Embedder, EmbeddingError, get_embedder
from app.ingestion.chunker import chunk_pages
from app.ingestion.loaders import SUPPORTED_EXTENSIONS, DocumentError, load_document
from app.llm.provider import LLMProvider, get_provider
from app.rag.prompts import NO_ANSWER, SYSTEM_PROMPT, build_user_message
from app.vectorstore.numpy_store import NumpyVectorStore

logger = logging.getLogger(__name__)

_CITATION = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._ -]")


class UploadError(Exception):
    """An upload was rejected. `status_code` is the HTTP status to report."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class IngestReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)


@dataclass
class AskResult:
    answer: str
    grounded: bool  # True if the answer cites at least one retrieved passage
    sources: list[tuple[int, Hit]]  # (citation number, hit)


class RagService:
    def __init__(
        self,
        settings: Settings,
        *,
        embedder: Embedder | None = None,
        store: NumpyVectorStore | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder or get_embedder(settings)
        self.min_score = (
            settings.min_score if settings.min_score is not None else self.embedder.default_min_score
        )
        self.docs_dir = Path(settings.docs_dir)
        self.store = store or NumpyVectorStore(Path(settings.index_dir))
        self._llm = llm

        self.store.load()
        if self.store.embedder_id not in (None, self.embedder.id):
            logger.warning(
                "Index was built with '%s' but the embedder is now '%s'; rebuilding.",
                self.store.embedder_id, self.embedder.id,
            )
            self.store.clear()
        self.store.embedder_id = self.embedder.id

    # --- ingestion -------------------------------------------------------------------

    def ingest(self, force: bool = False) -> IngestReport:
        """Sync the index with the files in docs_dir: add new, update changed, drop deleted."""
        report = IngestReport()
        self.docs_dir.mkdir(parents=True, exist_ok=True)

        files = sorted(
            p for p in self.docs_dir.iterdir()
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        for path in files:
            try:
                getattr(report, self.ingest_file(path, force=force)).append(path.name)
            except (DocumentError, EmbeddingError) as exc:
                logger.error("Could not ingest %s: %s", path.name, exc)
                report.failed[path.name] = str(exc)

        on_disk = {p.name for p in files}
        for name in list(self.store.documents()):
            if name not in on_disk:
                self.store.remove_document(name)
                report.removed.append(name)
        return report

    def ingest_file(self, path: Path, force: bool = False) -> str:
        """Index one file. Returns 'added', 'updated' or 'unchanged'."""
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        existing = self.store.documents().get(path.name)
        if existing and existing["sha256"] == digest and not force:
            return "unchanged"

        pages = load_document(path)
        pieces = chunk_pages(
            pages,
            default_section=path.stem.replace("_", " "),
            size=self.settings.chunk_size,
            overlap=self.settings.chunk_overlap,
        )
        chunks = [
            Chunk(
                id=f"{path.stem}-{ordinal:03d}", document=path.name, page=piece.page,
                section=piece.section, text=piece.text, ordinal=ordinal,
            )
            for ordinal, piece in enumerate(pieces)
        ]
        # Embedding the heading with the text lets "probation" match the "3. Probation" section.
        vectors = self.embedder.embed([f"{c.section}\n{c.text}" for c in chunks])
        self.store.replace_document(path.name, digest, len(pages), chunks, vectors)
        return "updated" if existing else "added"

    def add_upload(self, filename: str, data: bytes) -> str:
        """Validate and save an uploaded file into docs_dir, then index it. Returns the stored name."""
        name = self._safe_filename(filename)
        if len(data) > self.settings.max_upload_mb * 1024 * 1024:
            raise UploadError(f"File is larger than {self.settings.max_upload_mb} MB.", 413)
        if not data:
            raise UploadError("The file is empty.", 400)

        self.docs_dir.mkdir(parents=True, exist_ok=True)
        target = self.docs_dir / name
        previous = target.read_bytes() if target.exists() else None
        target.write_bytes(data)
        try:
            self.ingest_file(target)
        except (DocumentError, EmbeddingError):
            # Do not leave an unreadable file behind (or lose the version it replaced).
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                target.write_bytes(previous)
            raise
        return name

    @staticmethod
    def _safe_filename(filename: str | None) -> str:
        # Keep only the final path component: "../../etc/passwd" -> "passwd".
        name = Path((filename or "").replace("\\", "/")).name
        name = _UNSAFE_FILENAME_CHARS.sub("_", name).lstrip(".").strip()
        if not name:
            raise UploadError("A file name is required.", 400)
        if Path(name).suffix.lower() not in SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
            raise UploadError(f"Unsupported file type. Supported types: {allowed}.", 415)
        return name[-100:]

    def delete_document(self, filename: str) -> bool:
        """Remove a document from the store and delete its file on disk."""
        safe_name = Path(filename.replace("\\", "/")).name
        target = self.docs_dir / safe_name
        file_existed = False
        if target.is_file():
            target.unlink(missing_ok=True)
            file_existed = True
        store_existed = self.store.remove_document(safe_name)
        return file_existed or store_existed

    # --- search ----------------------------------------------------------------------

    def search(self, query: str, k: int | None = None) -> list[Hit]:
        """Top-k chunks by similarity, best first. Scores are returned, not filtered."""
        vector = self.embedder.embed([query])[0]
        return self.store.search(vector, k or self.settings.top_k)

    def documents(self) -> dict[str, dict]:
        return self.store.documents()

    # --- answering -------------------------------------------------------------------

    def get_llm(self) -> LLMProvider:
        if self._llm is None:
            self._llm = get_provider(self.settings)
        return self._llm

    def ask(self, question: str, k: int | None = None) -> AskResult:
        hits = [h for h in self.search(question, k) if h.score >= self.min_score]
        if not hits:
            # Nothing relevant was retrieved: do not ask the model, which would only guess.
            return AskResult(NO_ANSWER, grounded=False, sources=[])

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_message(question, hits)},
        ]
        reply = self.get_llm().chat(messages)
        answer = (reply.get("content") or "").strip() or NO_ANSWER

        numbered = list(enumerate(hits, start=1))
        cited = self._cited_numbers(answer, len(hits))
        if cited:
            return AskResult(answer, grounded=True, sources=[(n, h) for n, h in numbered if n in cited])
        # No valid citation: show what was retrieved so the reader can check for themselves.
        return AskResult(answer, grounded=False, sources=numbered)

    @staticmethod
    def _cited_numbers(answer: str, available: int) -> set[int]:
        numbers = {int(n) for group in _CITATION.findall(answer) for n in re.split(r"\s*,\s*", group)}
        return {n for n in numbers if 1 <= n <= available}
