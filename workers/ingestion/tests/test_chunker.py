from app.services.chunker import chunk_sections
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
