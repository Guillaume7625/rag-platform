"""Tests for IDF-aware sparse vectors in the worker embedder."""
from __future__ import annotations

from app.services.embedder import _sparse_from_text


def test_sparse_with_idf_changes_values() -> None:
    text = "the the the rare"
    without_idf = _sparse_from_text(text)
    idf_table = {idx: 0.1 for idx in without_idf["indices"]}
    with_idf = _sparse_from_text(text, idf_table=idf_table)

    # With all-low IDF, values should be scaled down.
    assert len(with_idf["values"]) == len(without_idf["values"])
    for v_idf, v_plain in zip(with_idf["values"], without_idf["values"]):
        assert v_idf < v_plain


def test_sparse_without_idf_matches_original() -> None:
    text = "hello world test"
    v1 = _sparse_from_text(text)
    v2 = _sparse_from_text(text, idf_table=None)
    assert v1 == v2


def test_sparse_idf_missing_index_defaults_to_one() -> None:
    text = "unique term"
    plain = _sparse_from_text(text)
    # Empty IDF table — every index gets idf.get(i, 1.0) = 1.0.
    with_empty = _sparse_from_text(text, idf_table={})
    assert plain["values"] == with_empty["values"]
