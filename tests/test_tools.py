# tests/test_tools.py
#
# Run all tests with:
#   pytest tests/
#
# Run only unit tests (no Groq API calls):
#   pytest tests/ -m "not integration"
#
# Each tool has at least one test per failure mode, as required by the project spec.

import pytest

from agent import _parse_query
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# =============================================================================
# _parse_query (agent.py helper)
# =============================================================================

def test_parse_query_price_and_size():
    """Full query — extracts description, size, and max_price correctly."""
    result = _parse_query("vintage graphic tee under $30, size M")
    assert result["size"] == "M"
    assert result["max_price"] == 30.0
    assert "vintage" in result["description"]
    assert "graphic" in result["description"]
    assert "$" not in result["description"]
    assert "size" not in result["description"].lower()

def test_parse_query_price_only():
    """Price-only query — size must be None."""
    result = _parse_query("flowy midi skirt under $40")
    assert result["max_price"] == 40.0
    assert result["size"] is None
    assert "flowy" in result["description"]
    assert "midi" in result["description"]

def test_parse_query_size_only():
    """Size-only query — max_price must be None."""
    result = _parse_query("black combat boots size 8")
    assert result["size"] == "8"
    assert result["max_price"] is None
    assert "black" in result["description"]
    assert "combat" in result["description"]

def test_parse_query_fallback_on_empty_description():
    """Stripping price/size/filler from a bare price query must not leave empty string."""
    result = _parse_query("under $30")
    assert result["description"]  # must not be empty
    assert len(result["description"]) > 0


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

@pytest.mark.integration
def test_suggest_outfit_with_wardrobe():
    """Happy path — should return a non-empty string with a real wardrobe."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert len(results) > 0  # make sure we have an item to test with
    suggestion = suggest_outfit(results[0], get_example_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0

@pytest.mark.integration
def test_suggest_outfit_empty_wardrobe():
    """Failure mode — empty wardrobe must return general advice, not crash."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    suggestion = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(suggestion, str)
    assert len(suggestion) > 0  # must never return empty string


# =============================================================================
# Tool 3: create_fit_card
# =============================================================================

@pytest.mark.integration
def test_create_fit_card_happy_path():
    """Happy path — valid outfit and item should return a non-empty caption."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    outfit = "Pair with baggy jeans and chunky sneakers for a 90s look."
    card = create_fit_card(outfit, results[0])
    assert isinstance(card, str)
    assert len(card) > 0

@pytest.mark.integration
def test_create_fit_card_empty_outfit():
    """Failure mode — empty outfit string must return error message, not crash."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    card = create_fit_card("", results[0])
    assert isinstance(card, str)
    assert "can't" in card.lower() or "error" in card.lower() or "without" in card.lower()

@pytest.mark.integration
def test_create_fit_card_whitespace_outfit():
    """Failure mode — whitespace-only outfit string must also be caught."""
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    card = create_fit_card("   ", results[0])
    assert isinstance(card, str)
    assert len(card) > 0  # returns error message, not empty string