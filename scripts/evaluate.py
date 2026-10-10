"""Measure retrieval quality with the current embedder and settings.

    python -m scripts.evaluate [--strict]

Indexes docs/ into a throwaway index (your saved index is untouched) and reports how often the
right passage is retrieved and whether off-topic questions are rejected. Re-run it after
switching EMBEDDING_PROVIDER, changing chunk sizes, or adjusting MIN_SCORE.
"""

import sys
import tempfile

from app.config import get_settings
from app.rag.evaluation import GroupResult, evaluate, load_cases
from app.rag.service import RagService


def _print_group(title: str, group: GroupResult, k: int) -> None:
    if not group.total:
        return
    print(f"\n{title} ({group.total} questions)")
    print(f"  right document is #1 result : {group.document_hit_at_1}/{group.total}")
    print(f"  right document in top {k}    : {group.document_hit_at_k}/{group.total}")
    print(f"  answer passage in top {k}    : {group.passage_hit_at_k}/{group.total}")
    print(f"  best score above MIN_SCORE  : {group.answerable}/{group.total}")
    for line in group.failures:
        print("   -", line)


def main() -> int:
    settings = get_settings().model_copy(update={"index_dir": tempfile.mkdtemp(prefix="eval-index-")})
    service = RagService(settings)
    ingest = service.ingest()
    if ingest.failed:
        print("Some documents failed to index:", ingest.failed)

    report = evaluate(service, load_cases(), k=settings.top_k)
    print(f"Embedder: {service.embedder.id} | top_k={report.k} | MIN_SCORE={report.min_score:.2f}")
    _print_group("In-scope, document vocabulary", report.in_scope, report.k)
    _print_group("Paraphrased, different vocabulary", report.paraphrased, report.k)

    print(f"\nOut-of-scope rejected: {report.out_of_scope_rejected}/{report.out_of_scope_total}")
    for line in report.out_of_scope_failures:
        print("   -", line)

    # Pass/fail only when a question phrased in the documents' own words no longer retrieves its
    # answer, which means chunking or embeddings broke. Paraphrases and off-topic rejection are
    # informational: they depend on the embedder (see README), and tests/test_retrieval_quality.py
    # guards the rest. Use --strict to fail on any problem.
    if "--strict" in sys.argv[1:]:
        return 1 if (report.in_scope.failures or report.out_of_scope_failures) else 0
    return 1 if report.in_scope.passage_hit_at_k < report.in_scope.total else 0


if __name__ == "__main__":
    sys.exit(main())
