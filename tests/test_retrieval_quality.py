"""Regression guard on retrieval quality using the offline embedder and data/eval_questions.json.

If one of these fails after a change to chunking, the embedder or the threshold, run
`python -m scripts.evaluate` to see exactly which questions regressed.
"""

import pytest

from app.rag.evaluation import evaluate, load_cases


@pytest.fixture
def report(service):
    return evaluate(service, load_cases(), k=4)


def test_every_in_scope_question_retrieves_the_answer_passage(report):
    assert report.in_scope.total >= 15
    assert report.in_scope.passage_hit_at_k == report.in_scope.total, report.in_scope.failures


def test_the_right_document_is_almost_always_ranked_first(report):
    assert report.in_scope.document_hit_at_1 >= report.in_scope.total - 1


def test_in_scope_questions_clear_the_relevance_threshold(report):
    assert report.in_scope.answerable == report.in_scope.total, report.in_scope.failures


def test_most_off_topic_questions_are_rejected(report):
    assert report.out_of_scope_rejected >= report.out_of_scope_total - 1, report.out_of_scope_failures


def test_paraphrased_questions_are_measured_but_not_required_to_pass(report):
    # The offline embedder is lexical, so paraphrases are expected to be hit-and-miss.
    # This only checks the group is being measured; see README for the numbers and why.
    assert report.paraphrased.total >= 5
