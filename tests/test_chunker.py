import re

import pytest

from app.ingestion.chunker import chunk_pages
from app.ingestion.loaders import Page


def test_numbered_headings_start_new_sections():
    pages = [Page(1, "Intro text before any heading.\n1. Purpose\nWhy this exists.\n2. Rules\nWhat to do.")]
    chunks = chunk_pages(pages, default_section="My Doc")

    assert [(c.section, c.text) for c in chunks] == [
        ("My Doc", "Intro text before any heading."),
        ("1. Purpose", "Why this exists."),
        ("2. Rules", "What to do."),
    ]


def test_markdown_headings():
    chunks = chunk_pages([Page(1, "# Leave\nTake it.\n## Sick Leave\nStay home.")], default_section="Doc")
    assert [(c.section, c.text) for c in chunks] == [("Leave", "Take it."), ("Sick Leave", "Stay home.")]


def test_body_lines_starting_with_numbers_are_not_headings():
    chunks = chunk_pages([Page(1, "1. Rules\n5 working days are allowed.\nand more.")], default_section="Doc")
    assert len(chunks) == 1
    assert "5 working days" in chunks[0].text


def test_chunks_never_cross_a_heading():
    chunks = chunk_pages([Page(1, "1. First Part\nalpha text.\n2. Second Part\nbeta text.")], default_section="Doc")
    assert len(chunks) == 2
    assert all(("alpha" in c.text) != ("beta" in c.text) for c in chunks)


def test_page_number_is_where_the_chunk_starts():
    pages = [Page(1, "1. Alpha\nfirst line"), Page(2, "second line\n2. Beta\nbeta text")]
    alpha, beta = chunk_pages(pages, default_section="Doc")

    assert (alpha.section, alpha.page, alpha.text) == ("1. Alpha", 1, "first line second line")
    assert (beta.section, beta.page) == ("2. Beta", 2)


def _numbered_sentences(count: int) -> str:
    return " ".join(f"Sentence number {i} is here." for i in range(count))


def test_long_section_is_split_with_overlap():
    chunks = chunk_pages([Page(1, "1. Long\n" + _numbered_sentences(30))], "Doc", size=200, overlap=60)

    assert len(chunks) > 3
    assert all(len(c.text) <= 200 for c in chunks)
    assert all(c.section == "1. Long" for c in chunks)

    numbers = [[int(n) for n in re.findall(r"number (\d+)", c.text)] for c in chunks]
    for previous, following in zip(numbers, numbers[1:]):
        assert following[0] <= previous[-1], "consecutive chunks should overlap"
        assert following[0] > previous[0], "each chunk must move forward"
    assert {n for group in numbers for n in group} == set(range(30)), "no sentence may be lost"


def test_chunk_page_follows_the_first_sentence():
    pages = [
        Page(1, "1. Long\n" + _numbered_sentences(10)),
        Page(2, " ".join(f"Later sentence {i} here." for i in range(10))),
    ]
    chunks = chunk_pages(pages, "Doc", size=200, overlap=40)
    assert chunks[0].page == 1
    assert chunks[-1].page == 2


def test_text_without_sentence_breaks_is_still_split():
    chunks = chunk_pages([Page(1, "1. Wall\n" + "word " * 500)], "Doc", size=300, overlap=50)
    assert len(chunks) > 5
    assert all(0 < len(c.text) <= 300 for c in chunks)


def test_a_single_word_longer_than_the_limit_does_not_hang():
    chunks = chunk_pages([Page(1, "1. Odd\n" + "x" * 1000)], "Doc", size=100, overlap=10)
    assert "".join(c.text for c in chunks).count("x") >= 1000


def test_empty_input():
    assert chunk_pages([], "Doc") == []
    assert chunk_pages([Page(1, "  \n\n ")], "Doc") == []


@pytest.mark.parametrize("size, overlap", [(0, 0), (100, 100), (100, 200), (100, -1)])
def test_invalid_sizes_are_rejected(size, overlap):
    with pytest.raises(ValueError):
        chunk_pages([Page(1, "text")], "Doc", size=size, overlap=overlap)
