from app.services.chunker import _tok, chunk_sections
from app.services.parser import ParsedSection


def test_chunk_sections_produces_parents_and_children() -> None:
    text = ("Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 300).strip()
    sections = [ParsedSection(order=0, page=1, section_title="Intro", text=text)]

    parents = chunk_sections(sections)

    assert len(parents) >= 1
    assert all(p.content for p in parents)
    assert all(len(p.children) >= 1 for p in parents)
    # Children should be meaningfully shorter than parents on average.
    avg_parent = sum(p.token_count for p in parents) / len(parents)
    avg_child = sum(c.token_count for p in parents for c in p.children) / sum(
        len(p.children) for p in parents
    )
    assert avg_child < avg_parent


def test_empty_input() -> None:
    parents = chunk_sections([])
    assert parents == []


def test_chunk_sections_french_text() -> None:
    text = (
        "L'économie française a connu une croissance modérée au cours du "
        "dernier trimestre, soutenue par la consommation des ménages et "
        "l'investissement des entreprises. "
    ) * 200
    sections = [ParsedSection(order=0, page=1, section_title="Économie", text=text.strip())]

    parents = chunk_sections(sections)

    assert len(parents) >= 1
    assert all(p.content for p in parents)
    assert all(len(p.children) >= 1 for p in parents)


def test_tok_char_based_heuristic() -> None:
    # _tok uses len(text) / 3.8 — verify against known inputs.
    assert _tok("hello") == max(1, int(5 / 3.8))  # 1
    assert _tok("a" * 38) == 10
    assert _tok("") == 1  # max(1, ...) ensures minimum of 1
