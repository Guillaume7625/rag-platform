"""Tests for the IDF service using fakeredis."""
from __future__ import annotations

import math

import fakeredis
import pytest

from app.services.idf_service import IDFService


@pytest.fixture()
def idf_svc(monkeypatch) -> IDFService:
    svc = IDFService.__new__(IDFService)
    svc._redis = fakeredis.FakeRedis(decode_responses=True)
    svc._cache = {}
    svc._cache_ts = 0.0
    return svc


class TestIDFService:
    def test_update_increments_counts(self, idf_svc: IDFService) -> None:
        idf_svc.update_from_document({1, 2, 3})
        assert int(idf_svc._redis.get("idf:doc_count")) == 1
        assert int(idf_svc._redis.hget("idf:df", "1")) == 1

        idf_svc.update_from_document({2, 4})
        assert int(idf_svc._redis.get("idf:doc_count")) == 2
        assert int(idf_svc._redis.hget("idf:df", "2")) == 2
        assert int(idf_svc._redis.hget("idf:df", "4")) == 1

    def test_rebuild_produces_correct_idf(self, idf_svc: IDFService) -> None:
        # 3 documents: token 0 appears in all 3, token 1 in 1.
        for _ in range(3):
            idf_svc.update_from_document({0})
        idf_svc.update_from_document({1})

        idf_svc.rebuild_idf_table()

        table = idf_svc.get_idf_table()
        # N=4 docs total (3 + 1)
        expected_0 = math.log((4 + 1) / (3 + 1))  # common term
        expected_1 = math.log((4 + 1) / (1 + 1))  # rare term
        assert abs(table[0] - expected_0) < 1e-6
        assert abs(table[1] - expected_1) < 1e-6
        assert table[1] > table[0]  # rare terms get higher IDF

    def test_get_idf_table_returns_empty_before_rebuild(self, idf_svc: IDFService) -> None:
        assert idf_svc.get_idf_table() == {}

    def test_get_idf_table_caches_in_process(self, idf_svc: IDFService) -> None:
        idf_svc.update_from_document({5})
        idf_svc.rebuild_idf_table()
        table1 = idf_svc.get_idf_table()
        assert 5 in table1

        # Delete from Redis; cached version should still be returned.
        idf_svc._redis.delete("idf:global")
        table2 = idf_svc.get_idf_table()
        assert table2 == table1
