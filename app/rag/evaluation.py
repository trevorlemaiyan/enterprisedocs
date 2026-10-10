"""Retrieval evaluation: does the right passage come back, and are off-topic questions rejected?

Measures retrieval only (no LLM), so it is fast, free and deterministic. Run it after changing
chunking, embeddings or MIN_SCORE.

Three question groups:
  in_scope     questions phrased with the documents' own vocabulary
  paraphrased  the same kind of question phrased with DIFFERENT words (holiday vs annual leave)
  out_of_scope questions the documents cannot answer; these should score below MIN_SCORE

Honest limits: the questions were written by the same person who wrote the documents, and the
set is small, so scores are optimistic compared with real employee questions.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.rag.service import RagService

DEFAULT_CASES = Path(__file__).resolve().parents[2] / "data" / "eval_questions.json"


@dataclass
class GroupResult:
    total: int = 0
    document_hit_at_1: int = 0
    document_hit_at_k: int = 0
    passage_hit_at_k: int = 0
    answerable: int = 0  # best score cleared MIN_SCORE
    failures: list[str] = field(default_factory=list)


@dataclass
class EvalReport:
    k: int
    min_score: float
    in_scope: GroupResult = field(default_factory=GroupResult)
    paraphrased: GroupResult = field(default_factory=GroupResult)
    out_of_scope_total: int = 0
    out_of_scope_rejected: int = 0
    out_of_scope_failures: list[str] = field(default_factory=list)


def load_cases(path: Path = DEFAULT_CASES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _run_group(service: RagService, cases: list[dict], k: int) -> GroupResult:
    result = GroupResult()
    for case in cases:
        hits = service.search(case["question"], k)
        result.total += 1

        if hits and hits[0].chunk.document == case["expected_document"]:
            result.document_hit_at_1 += 1
        if any(h.chunk.document == case["expected_document"] for h in hits):
            result.document_hit_at_k += 1

        phrase = case["expected_contains"].lower()
        if any(phrase in h.chunk.text.lower() for h in hits):
            result.passage_hit_at_k += 1
        else:
            top = f"{hits[0].chunk.document} / {hits[0].chunk.section}" if hits else "nothing"
            result.failures.append(f"MISS  {case['question']!r} -> top result: {top}")

        if hits and hits[0].score >= service.min_score:
            result.answerable += 1
        else:
            score = f"{hits[0].score:.2f}" if hits else "n/a"
            result.failures.append(f"BELOW THRESHOLD  {case['question']!r} (best score {score})")
    return result


def evaluate(service: RagService, cases: dict, k: int = 4) -> EvalReport:
    report = EvalReport(k=k, min_score=service.min_score)
    report.in_scope = _run_group(service, cases["in_scope"], k)
    report.paraphrased = _run_group(service, cases.get("paraphrased", []), k)

    for question in cases["out_of_scope"]:
        hits = service.search(question, k)
        report.out_of_scope_total += 1
        if not hits or hits[0].score < service.min_score:
            report.out_of_scope_rejected += 1
        else:
            report.out_of_scope_failures.append(
                f"NOT REJECTED  {question!r} -> {hits[0].chunk.document} / {hits[0].chunk.section} ({hits[0].score:.2f})"
            )
    return report
