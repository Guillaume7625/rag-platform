from app.services.query_router_service import decide_mode, decompose


def test_standard_mode_for_factoid() -> None:
    assert decide_mode("Quel est le préavis du contrat ?") == "standard"


def test_deep_mode_for_comparison() -> None:
    assert decide_mode("Compare la politique de congés 2024 vs 2025") == "deep"


def test_forced_mode_wins() -> None:
    assert decide_mode("Hello world", forced="deep") == "deep"


def test_decompose_splits_on_et() -> None:
    parts = decompose("Politique RH et code de conduite et voyages")
    assert len(parts) == 3
