import pytest

from app.ingestion.loaders import DocumentError, Page, _strip_repeated_lines, load_document
from tests.conftest import REAL_DOCS

reportlab_canvas = pytest.importorskip("reportlab.pdfgen.canvas")


def make_pdf(path, pages: list[str]) -> None:
    pdf = reportlab_canvas.Canvas(str(path))
    for number, text in enumerate(pages, start=1):
        y = 800
        for line in text.splitlines():
            pdf.drawString(72, y, line)
            y -= 16
        pdf.drawString(72, 40, f"Acme Confidential - Page {number}")
        pdf.showPage()
    pdf.save()


def test_text_and_markdown_files(tmp_path):
    (tmp_path / "a.txt").write_text("hello world", encoding="utf-8")
    (tmp_path / "b.md").write_text("# Title\nbody", encoding="utf-8")

    assert load_document(tmp_path / "a.txt") == [Page(1, "hello world")]
    assert load_document(tmp_path / "b.md")[0].text == "# Title\nbody"


def test_unsupported_extension(tmp_path):
    (tmp_path / "x.exe").write_bytes(b"MZ")
    with pytest.raises(DocumentError, match="Unsupported file type"):
        load_document(tmp_path / "x.exe")


def test_empty_text_file(tmp_path):
    (tmp_path / "empty.txt").write_text("  \n ", encoding="utf-8")
    with pytest.raises(DocumentError, match="no extractable text"):
        load_document(tmp_path / "empty.txt")


def test_corrupt_pdf_gives_a_clean_error(tmp_path):
    (tmp_path / "bad.pdf").write_bytes(b"%PDF-1.4\nthis is not really a pdf")
    with pytest.raises(DocumentError):
        load_document(tmp_path / "bad.pdf")


def test_pdf_pages_and_footer_removal(tmp_path):
    make_pdf(tmp_path / "doc.pdf", ["1. Intro\nFirst page body.", "Second page body.", "Third page body."])
    pages = load_document(tmp_path / "doc.pdf")

    assert [p.number for p in pages] == [1, 2, 3]
    assert "First page body." in pages[0].text
    assert all("Confidential" not in p.text for p in pages), "running footer should be stripped"


def test_footer_is_kept_for_single_page_documents(tmp_path):
    make_pdf(tmp_path / "one.pdf", ["Only page."])
    assert "Confidential" in load_document(tmp_path / "one.pdf")[0].text


def test_repeated_line_removal_ignores_lines_that_are_not_repeated():
    pages = [Page(1, "Header 1\nunique one"), Page(2, "Header 2\nunique two"), Page(3, "Header 3\nunique three")]
    cleaned = _strip_repeated_lines(pages)
    assert [p.text for p in cleaned] == ["unique one", "unique two", "unique three"]


def test_the_sample_documents_load():
    names = {"HR_Policy.pdf", "Leave_Policy.pdf", "IT_Support_Guide.pdf", "Procurement_Policy.pdf"}
    assert {p.name for p in REAL_DOCS.glob("*.pdf")} == names
    for name in names:
        pages = load_document(REAL_DOCS / name)
        assert len(pages) == 2
        assert all("Fictional sample document" not in p.text for p in pages)
