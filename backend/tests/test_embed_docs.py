import pytest

from app.retrieval.build_docs import build_docs
from app.retrieval.embed_docs import reset_index_cache, retrieve_context, search


@pytest.fixture(autouse=True)
def fresh_index():
    build_docs()
    reset_index_cache()
    yield
    reset_index_cache()


def test_search_ranks_the_matching_dish_first():
    results = search("what is in the peri-peri chicken")
    assert results
    assert results[0][0] == "peri-peri-chicken.md"


def test_search_finds_fish_and_chips_for_imported_fish_query():
    results = search("imported fish margin")
    assert results[0][0] == "fish-chips.md"


def test_search_returns_both_sadza_dishes():
    results = search("sadza options", top_k=5)
    names = [r[0] for r in results]
    assert "sadza-nemuriwo.md" in names
    assert "sadza-beef-stew.md" in names


def test_search_returns_nothing_for_unrelated_query():
    assert search("roller coaster theme park") == []


def test_search_respects_top_k():
    assert len(search("chicken", top_k=1)) == 1


def test_retrieve_context_joins_top_matches():
    context = retrieve_context("peri-peri chicken", top_k=2)
    assert context is not None
    assert "Peri-Peri Chicken" in context


def test_retrieve_context_none_when_no_match():
    assert retrieve_context("roller coaster theme park") is None
