"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — inputs, tool results, and any error that caused early exit.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex patterns.

    Examples:
        "vintage graphic tee under $30, size M"
            → {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}

        "flowy midi skirt under $40"
            → {"description": "flowy midi skirt", "size": None, "max_price": 40.0}

        "black combat boots size 8"
            → {"description": "black combat boots", "size": "8", "max_price": None}

    Returns a dict with keys: description (str), size (str|None), max_price (float|None)
    """

    # --- Extract max_price ---
    # Matches patterns like "under $30", "under $30.50", "$30", "< $30"
    price_match = re.search(r"(?:under|<|max|below)?\s*\$(\d+(?:\.\d+)?)", query, re.IGNORECASE)
    max_price = float(price_match.group(1)) if price_match else None

    # --- Extract size ---
    # Matches patterns like "size M", "size XL", "size 8", "size S/M"
    size_match = re.search(r"\bsize\s+([A-Z0-9]{1,5}(?:/[A-Z0-9]{1,5})?)\b", query, re.IGNORECASE)
    size = size_match.group(1).upper() if size_match else None

    # --- Extract description ---
    # Start with the full query, then strip out the parts we already parsed
    description = query

    # Remove price phrases like "under $30" or "$30"
    description = re.sub(r"(?:under|<|max|below)?\s*\$\d+(?:\.\d+)?", "", description, flags=re.IGNORECASE)

    # Remove size phrases like "size M" or "size S/M"
    description = re.sub(r"\bsize\s+[A-Z0-9]{1,5}(?:/[A-Z0-9]{1,5})?\b", "", description, flags=re.IGNORECASE)

    # Remove common filler words that don't help with search
    description = re.sub(r"\b(i'm|im|looking|for|a|an|the|in|and|or|,)\b", "", description, flags=re.IGNORECASE)

    # Clean up extra whitespace left behind
    description = " ".join(description.split()).strip()

    # Fallback: if stripping left nothing, use the original query
    if not description:
        description = query

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes.
        Check session["error"] first — if not None, the interaction ended early
        and outfit_suggestion / fit_card will be None.

    Planning loop steps (matches planning.md spec):
        1. Initialize session
        2. Parse query → extract description, size, max_price
        3. Call search_listings → if empty, set error and return early
        4. Select top result as selected_item
        5. Call suggest_outfit with selected_item and wardrobe
        6. Call create_fit_card with outfit_suggestion and selected_item
        7. Return completed session
    """

    # Step 1: Initialize a fresh session for this interaction
    session = _new_session(query, wardrobe)

    # Step 2: Parse the user query to extract structured search parameters
    parsed = _parse_query(query)
    session["parsed"] = parsed  # store so it's visible for debugging

    # Step 3: Search for matching listings using the parsed parameters
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    # BRANCH: if no results found, set error and return early
    # The agent must NOT call suggest_outfit with empty input
    if not results:
        # Build a helpful message based on what filters were active
        filters_used = []
        if parsed["size"]:
            filters_used.append(f"size {parsed['size']}")
        if parsed["max_price"]:
            filters_used.append(f"under ${parsed['max_price']:.0f}")

        filter_hint = f" (filtered by {', '.join(filters_used)})" if filters_used else ""
        session["error"] = (
            f"No listings found for '{parsed['description']}'{filter_hint}. "
            f"Try broadening your search — remove the size filter or increase your price range."
        )
        return session  # early exit — outfit_suggestion and fit_card remain None

    # Step 4: Select the top result (highest relevance score) as the item to use
    session["selected_item"] = results[0]

    # Step 5: Generate outfit suggestions using the selected item and the user's wardrobe
    # State flows here: selected_item from step 4, wardrobe from session init
    outfit_suggestion = suggest_outfit(
        new_item=session["selected_item"],
        wardrobe=session["wardrobe"],
    )
    session["outfit_suggestion"] = outfit_suggestion

    # Step 6: Generate a shareable fit card caption using the outfit and item
    # State flows here: outfit_suggestion from step 5, selected_item from step 4
    fit_card = create_fit_card(
        outfit=session["outfit_suggestion"],
        new_item=session["selected_item"],
    )
    session["fit_card"] = fit_card

    # Step 7: Return the completed session — all fields populated on happy path
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed: {session['parsed']}")
        print(f"\nFound: {session['selected_item']['title']} — ${session['selected_item']['price']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")
    print(f"fit_card is None: {session2['fit_card'] is None}")


# =============================================================================
# ORIGINAL STARTER INSTRUCTIONS (preserved for reference)
# =============================================================================
#
# TODO — implement run_agent() using the planning loop you designed in planning.md:
#
#     Step 1: Initialize the session with _new_session().
#
#     Step 2: Parse the user's query to extract a description, size, and
#             max_price. You can use regex, string splitting, or ask the LLM
#             to parse it — document your choice in planning.md.
#             Store the result in session["parsed"].
#
#     Step 3: Call search_listings() with the parsed parameters.
#             Store results in session["search_results"].
#             If no results: set session["error"] to a helpful message and
#             return the session early. Do NOT proceed to suggest_outfit
#             with empty input.
#
#     Step 4: Select the item to use (e.g., the top result).
#             Store it in session["selected_item"].
#
#     Step 5: Call suggest_outfit() with the selected item and wardrobe.
#             Store the result in session["outfit_suggestion"].
#
#     Step 6: Call create_fit_card() with the outfit suggestion and selected item.
#             Store the result in session["fit_card"].
#
#     Step 7: Return the session.