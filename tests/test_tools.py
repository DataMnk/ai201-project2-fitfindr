# tests/test_tools.py
#
# Run all tests with:
#   pytest tests/
#
# Each tool has at least one test per failure mode, as required by the project spec.

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# =============================================================================
# Tool 1: search_listings
# =============================================================================

def test_search_returns_results():
    """Happy path — a broad query should return at least one result."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    """Failure mode — impossible query must return [] without crashing."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    """All returned items must respect the max_price ceiling."""
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)

def test_search_size_filter():
    """All returned items must contain the requested size string."""
    results = search_listings("top", size="M", max_price=None)
    for item in results:
        assert "m" in item["size"].lower()

def test_search_returns_list_on_no_match():
    """Return type must always be a list, even when empty."""
    results = search_listings("xyznotarealthing", size=None, max_price=None)
    assert isinstance(results, list)


# =============================================================================
# Tool 2: suggest_outfit
# =============================================================================

def test_suggest_outfit_with_wardrobe():
    """Happy path — should return a non-empty string with a real wardrobe."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert len(results) > 0  # make sure we have an item to test with
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0

def test_suggest_outfit_empty_wardrobe():
    """Failure mode — empty wardrobe must return general advice, not crash."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0  # must never return empty string


# =============================================================================
# Tool 3: create_fit_card
# =============================================================================

def test_create_fit_card_happy_path():
    """Happy path — valid outfit and item should return a non-empty caption."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    outfit = "Pair with baggy jeans and chunky sneakers for a 90s look."
    card = create_fit_card(outfit, results[0])
    assert isinstance(card, str)
    assert len(card) > 0

def test_create_fit_card_empty_outfit():
    """Failure mode — empty outfit string must return error message, not crash."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    card = create_fit_card("", results[0])
    assert isinstance(card, str)
    assert "can't" in card.lower() or "error" in card.lower() or "without" in card.lower()

def test_create_fit_card_whitespace_outfit():
    """Failure mode — whitespace-only outfit string must also be caught."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    card = create_fit_card("   ", results[0])
    assert isinstance(card, str)
    assert len(card) > 0  # returns error message, not empty string