"""Tests for the Qdrant ACL filter contract in qdrant_service.py.

Contract verified from hybrid_search():
- tenant_id: FieldCondition(key="tenant_id", match=MatchValue(value=str(tenant_id)))
  Always present in must[].
- allowed_roles: FieldCondition(key="allowed_roles", match=MatchAny(any=allowed_roles))
  Present when allowed_roles is truthy.
- tags: FieldCondition(key="tags", match=MatchAny(any=tag_filters))
  Present when tag_filters is truthy.
- The same Filter object is passed to BOTH prefetches (dense and sparse).
"""
from __future__ import annotations

import ast
import pathlib

SRC = pathlib.Path(__file__).resolve().parent.parent / "app" / "services" / "qdrant_service.py"


def _read_source() -> str:
    return SRC.read_text()


class TestACLFilterFields:
    """The ACL filter must use the correct field names and match types."""

    def test_tenant_id_field_present(self):
        source = _read_source()
        assert 'key="tenant_id"' in source

    def test_tenant_id_uses_match_value(self):
        source = _read_source()
        assert "MatchValue" in source
        lines = source.splitlines()
        for line in lines:
            if "tenant_id" in line and "FieldCondition" in line:
                assert "MatchValue" in line, "tenant_id must use MatchValue"
                break

    def test_allowed_roles_field_present(self):
        source = _read_source()
        assert 'key="allowed_roles"' in source

    def test_allowed_roles_uses_match_any(self):
        source = _read_source()
        lines = source.splitlines()
        for line in lines:
            if "allowed_roles" in line and "FieldCondition" in line:
                assert "MatchAny" in line, "allowed_roles must use MatchAny"
                break

    def test_tags_field_present(self):
        source = _read_source()
        assert 'key="tags"' in source

    def test_tags_uses_match_any(self):
        source = _read_source()
        lines = source.splitlines()
        for line in lines:
            if '"tags"' in line and "FieldCondition" in line:
                assert "MatchAny" in line, "tags must use MatchAny"
                break


class TestACLFilterOnBothPrefetches:
    """The same filter must be applied to both dense and sparse prefetches."""

    def test_filter_variable_used_on_both_prefetches(self):
        source = _read_source()
        assert source.count("filter=flt") == 2, (
            "filter=flt must appear exactly twice (once per prefetch)"
        )

    def test_structural_equality_of_filter(self):
        """Both prefetches must receive structurally equal filters.

        Since the code uses the same variable 'flt' for both, we verify
        by AST that both Prefetch calls reference the same filter name.
        """
        source = _read_source()
        tree = ast.parse(source)
        filter_names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                is_prefetch = False
                if isinstance(func, ast.Attribute) and func.attr == "Prefetch":
                    is_prefetch = True
                if isinstance(func, ast.Name) and func.id == "Prefetch":
                    is_prefetch = True
                if is_prefetch:
                    for kw in node.keywords:
                        if kw.arg == "filter":
                            if isinstance(kw.value, ast.Name):
                                filter_names.append(kw.value.id)
        assert len(filter_names) == 2, (
            f"Expected 2 Prefetch filter= args, found {len(filter_names)}"
        )
        assert filter_names[0] == filter_names[1], (
            f"Both prefetches must use the same filter variable, "
            f"got {filter_names[0]!r} and {filter_names[1]!r}"
        )


class TestACLFilterConditionals:
    """Tags and allowed_roles are conditionally added."""

    def test_tags_is_optional(self):
        source = _read_source()
        assert "tag_filters" in source
        assert "if tag_filters:" in source, (
            "tags filter must be conditionally added"
        )

    def test_allowed_roles_is_conditional(self):
        source = _read_source()
        assert "if allowed_roles:" in source, (
            "allowed_roles filter must be conditionally added"
        )
