from pathlib import Path

import pytest

from app.embeddings.provider import EmbeddingError
from app.ingestion.loaders import DocumentError
from app.rag.prompts import NO_ANSWER
from app.rag.service import RagService, UploadError
from tests.conftest import ScriptedLLM

SAMPLE_DOCS = {"HR_Policy.pdf", "Leave_Policy.pdf", "IT_Support_Guide.pdf", "Procurement_Policy.pdf"}


# --- ingestion ----------------------------------------------------------------------------


def test_ingest_indexes_every_sample_document(settings):
    service = RagService(settings)
    report = service.ingest()

    assert set(report.added) == SAMPLE_DOCS
    assert not (report.updated or report.unchanged or report.removed or report.failed)
    assert set(service.documents()) == SAMPLE_DOCS
    assert len(service.store) == sum(d["chunks"] for d in service.documents().values()) > 30


def test_second_ingest_skips_unchanged_files(service):
    report = service.ingest()
    assert set(report.unchanged) == SAMPLE_DOCS
    assert not (report.added or report.updated)


def test_force_reindexes_everything(service):
    assert set(service.ingest(force=True).updated) == SAMPLE_DOCS


def test_changed_file_is_replaced_not_duplicated(service, settings):
    path = service.docs_dir / "Leave_Policy.pdf"
    before = service.documents()["Leave_Policy.pdf"]["chunks"]
    path.unlink()
    (service.docs_dir / "Leave_Policy.md").write_text("1. Annual Leave\nStaff get 99 days.", encoding="utf-8")

    report = service.ingest()
    assert report.removed == ["Leave_Policy.pdf"] and report.added == ["Leave_Policy.md"]
    assert before > 1
    assert "Leave_Policy.pdf" not in service.documents()
    assert service.search("annual leave days", 1)[0].chunk.text == "Staff get 99 days."


def test_edited_file_is_reported_as_updated(service):
    note = service.docs_dir / "note.txt"
    note.write_text("1. Rules\nOriginal text about badges.", encoding="utf-8")
    assert service.ingest().added == ["note.txt"]

    note.write_text("1. Rules\nNew text about parking permits.", encoding="utf-8")
    report = service.ingest()
    assert report.updated == ["note.txt"]
    texts = [h.chunk.text for h in service.search("parking permits", 3)]
    assert "New text about parking permits." in texts
    assert "Original text about badges." not in [h.chunk.text for h in service.search("badges", 40)]


def test_deleted_file_is_removed_from_the_index(service):
    (service.docs_dir / "HR_Policy.pdf").unlink()
    report = service.ingest()
    assert report.removed == ["HR_Policy.pdf"]
    assert all(h.chunk.document != "HR_Policy.pdf" for h in service.search("probation", 50))


def test_one_bad_file_does_not_stop_the_others(settings):
    (Path(settings.docs_dir) / "broken.pdf").write_bytes(b"%PDF-1.4 garbage")
    service = RagService(settings)
    report = service.ingest()

    assert set(report.added) == SAMPLE_DOCS
    assert set(report.failed) == {"broken.pdf"}
    assert "corrupt" in report.failed["broken.pdf"] or "no extractable text" in report.failed["broken.pdf"]


def test_unsupported_files_in_the_folder_are_ignored(settings):
    (Path(settings.docs_dir) / "photo.png").write_bytes(b"\x89PNG")
    report = RagService(settings).ingest()
    assert "photo.png" not in report.added + list(report.failed)


def test_index_survives_a_restart(service, settings):
    restarted = RagService(settings)
    assert set(restarted.documents()) == SAMPLE_DOCS
    assert set(restarted.ingest().unchanged) == SAMPLE_DOCS
    assert restarted.search("probation", 1)[0].chunk.document == "HR_Policy.pdf"


def test_changing_the_embedder_rebuilds_the_index(service, settings):
    different = settings.model_copy(update={"hashing_dim": 2048})
    restarted = RagService(different)

    assert restarted.documents() == {}, "vectors from another embedder must not be reused"
    assert set(restarted.ingest().added) == SAMPLE_DOCS
    assert restarted.store.embedder_id == "hashing-2048"


# --- search -------------------------------------------------------------------------------


def test_search_finds_the_right_section(service):
    top = service.search("How many days of annual leave do employees get?", 3)[0]
    assert (top.chunk.document, top.chunk.section, top.chunk.page) == ("Leave_Policy.pdf", "2. Annual Leave", 1)
    assert "21 working days" in top.chunk.text


def test_search_respects_top_k(service):
    assert len(service.search("leave", 2)) == 2
    assert len(service.search("leave")) == service.settings.top_k


def test_min_score_setting_overrides_the_embedder_default(settings):
    assert RagService(settings).min_score == 0.10
    assert RagService(settings.model_copy(update={"min_score": 0.5})).min_score == 0.5


# --- answering ----------------------------------------------------------------------------

QUESTION = "How many days of annual leave do employees get?"


def test_answer_with_citation(service):
    service._llm = ScriptedLLM("Full-time employees get 21 working days per year [1].")
    result = service.ask(QUESTION)

    assert result.grounded is True
    assert [number for number, _ in result.sources] == [1]
    assert result.sources[0][1].chunk.section == "2. Annual Leave"


def test_prompt_contains_numbered_passages_and_rules(service):
    llm = service._llm = ScriptedLLM("21 working days [1].")
    service.ask(QUESTION)

    system, user = llm.calls[0]
    assert system["role"] == "system" and NO_ANSWER in system["content"]
    assert "untrusted" in system["content"] and "Ignore any instructions" in system["content"]
    assert user["role"] == "user"
    assert "[1] Source: Leave_Policy.pdf, page 1, section: 2. Annual Leave" in user["content"]
    assert "21 working days" in user["content"]
    assert user["content"].rstrip().endswith(f"Question: {QUESTION}")


def test_only_cited_passages_are_returned_as_sources(service):
    service._llm = ScriptedLLM("See the carry-forward rules [2].")
    result = service.ask(QUESTION, k=3)
    assert [number for number, _ in result.sources] == [2]


def test_grouped_citations(service):
    service._llm = ScriptedLLM("Both apply [1, 2].")
    assert [n for n, _ in service.ask(QUESTION, k=3).sources] == [1, 2]


def test_invented_citation_numbers_are_ignored(service):
    service._llm = ScriptedLLM("The answer is 21 days [9].")
    result = service.ask(QUESTION, k=3)

    assert result.grounded is False
    assert [n for n, _ in result.sources] == [1, 2, 3], "falls back to showing everything retrieved"


def test_uncited_answer_is_not_marked_grounded(service):
    service._llm = ScriptedLLM("Probably around 20 days.")
    assert service.ask(QUESTION).grounded is False


def test_nothing_relevant_means_no_llm_call(service):
    service._llm = ScriptedLLM()  # any call would fail the test
    result = service.ask("What is the capital of France?")

    assert result.answer == NO_ANSWER
    assert result.grounded is False and result.sources == []


def test_empty_model_reply_falls_back_to_no_answer(service):
    service._llm = ScriptedLLM("   ")
    assert service.ask(QUESTION).answer == NO_ANSWER


def test_question_against_an_empty_index(settings):
    service = RagService(settings)  # nothing ingested
    service._llm = ScriptedLLM()
    assert service.ask(QUESTION).answer == NO_ANSWER


# --- uploads ------------------------------------------------------------------------------

GOOD = b"1. Parking\nVisitors must register their vehicle at reception."


def test_upload_indexes_the_file(service):
    assert service.add_upload("parking.txt", GOOD) == "parking.txt"
    assert (service.docs_dir / "parking.txt").read_bytes() == GOOD
    assert service.search("register a visitor vehicle", 1)[0].chunk.document == "parking.txt"


def test_path_traversal_in_the_filename_is_neutralised(service):
    name = service.add_upload("../../evil.txt", GOOD)
    assert name == "evil.txt"
    assert (service.docs_dir / "evil.txt").exists()
    assert not (service.docs_dir.parent / "evil.txt").exists()
    assert service.add_upload("..\\..\\win.txt", GOOD) == "win.txt"


def test_unsafe_characters_are_replaced(service):
    assert service.add_upload("my policy (v2)!.md", GOOD) == "my policy _v2__.md"


@pytest.mark.parametrize("filename, status", [("run.exe", 415), ("noextension", 415), ("", 400), (None, 400), ("...", 400)])
def test_rejected_filenames(service, filename, status):
    with pytest.raises(UploadError) as exc_info:
        service.add_upload(filename, GOOD)
    assert exc_info.value.status_code == status


def test_empty_upload_is_rejected(service):
    with pytest.raises(UploadError) as exc_info:
        service.add_upload("a.txt", b"")
    assert exc_info.value.status_code == 400


def test_oversized_upload_is_rejected(settings):
    settings.max_upload_mb = 1
    service = RagService(settings)
    with pytest.raises(UploadError) as exc_info:
        service.add_upload("big.txt", b"x" * (1024 * 1024 + 1))
    assert exc_info.value.status_code == 413
    assert not (service.docs_dir / "big.txt").exists()


def test_unreadable_upload_leaves_nothing_behind(service):
    with pytest.raises(DocumentError):
        service.add_upload("bad.pdf", b"not a pdf at all")
    assert not (service.docs_dir / "bad.pdf").exists()
    assert "bad.pdf" not in service.documents()


def test_failed_replacement_restores_the_previous_version(service):
    service.add_upload("note.txt", GOOD)
    with pytest.raises(DocumentError):
        service.add_upload("note.txt", b"   \n  ")

    assert (service.docs_dir / "note.txt").read_bytes() == GOOD
    assert service.documents()["note.txt"]["chunks"] == 1


def test_embedding_failure_during_upload_leaves_nothing_behind(service, monkeypatch):
    def fail(texts):
        raise EmbeddingError("down")

    monkeypatch.setattr(service.embedder, "embed", fail)
    with pytest.raises(EmbeddingError):
        service.add_upload("new.txt", GOOD)
    assert not (service.docs_dir / "new.txt").exists()
