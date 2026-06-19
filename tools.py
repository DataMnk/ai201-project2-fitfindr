"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Returns a list sorted by relevance score (highest first).
    Returns [] if nothing matches — never raises an exception.
    """

    # Step 1: Load all 40 listings from the JSON file
    listings = load_listings()

    # Step 2: Apply hard filters — price and size must match exactly if provided
    filtered = []
    for item in listings:

        # Filter by max price — skip anything above the ceiling
        if max_price is not None and item["price"] > max_price:
            continue

        # Filter by size — case-insensitive substring match
        # e.g. "M" matches "S/M" or "M/L", "L" matches "L/XL"
        if size is not None:
            item_size = (item.get("size") or "").lower()
            if size.lower() not in item_size:
                continue

        filtered.append(item)

    # Step 3: Score each remaining listing by keyword overlap with description
    # We search across: title, description, style_tags, category, brand
    keywords = description.lower().split()

    scored = []
    for item in filtered:
        # Build a single searchable text blob from all relevant fields
        searchable = " ".join([
            item.get("title", ""),
            item.get("description", ""),
            item.get("category", ""),
            item.get("brand", "") or "",          # brand can be None
            " ".join(item.get("style_tags", [])), # style_tags is a list
            " ".join(item.get("colors", [])),     # colors is also a list
        ]).lower()

        # Count how many query keywords appear in the searchable text
        score = sum(1 for keyword in keywords if keyword in searchable)
        scored.append((score, item))

    # Step 4: Drop items with zero keyword matches (totally irrelevant)
    scored = [(score, item) for score, item in scored if score > 0]

    # Step 5: Sort by score descending — best match first
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return just the listing dicts, without the scores
    return [item for score, item in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    If wardrobe is empty, gives general styling advice instead.
    Never raises an exception or returns an empty string.
    """

    # Check whether the wardrobe has any items at all
    wardrobe_items = wardrobe.get("items", [])
    wardrobe_is_empty = len(wardrobe_items) == 0

    # Build a readable summary of the new thrifted item for the prompt
    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Condition: {new_item.get('condition', 'unknown')}"
    )

    if wardrobe_is_empty:
        # No wardrobe — ask for general styling advice instead
        prompt = f"""
You are a thrift-savvy personal stylist. A user just found this secondhand item:

{item_summary}

They haven't described their wardrobe yet. Give them 1–2 specific outfit ideas for this item —
describe what kinds of bottoms, shoes, and outerwear would pair well, and what vibe each look goes for.
Be specific and conversational, not generic.
""".strip()

    else:
        # Format wardrobe items into a readable list for the prompt
        wardrobe_lines = []
        for w in wardrobe_items:
            line = f"- {w['name']} ({w['category']})"
            # Add style notes if available
            if w.get("notes"):
                line += f" — {w['notes']}"
            wardrobe_lines.append(line)

        wardrobe_text = "\n".join(wardrobe_lines)

        prompt = f"""
You are a thrift-savvy personal stylist. A user just found this secondhand item:

{item_summary}

Here is their current wardrobe:
{wardrobe_text}

Suggest 1–2 complete outfit combinations using this new item paired with specific pieces
from their wardrobe above. Name the exact wardrobe pieces you're combining. Be specific about
the vibe, how to style each piece (tuck, layer, roll, etc.), and what occasions it works for.
Keep it conversational and specific — not generic fashion advice.
""".strip()

    # Call the Groq LLM
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=400,
        )
        result = response.choices[0].message.content.strip()

        # Guard: never return empty string even if LLM returns nothing
        if not result:
            return "Couldn't generate outfit suggestions right now — try again."

        return result

    except Exception as e:
        return f"Couldn't generate outfit suggestions right now — try again. (Error: {e})"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable OOTD caption for the thrifted find.

    Returns a 2–4 sentence casual caption.
    If outfit is empty, returns an error string — never raises an exception.
    """

    # Step 1: Guard against empty outfit string BEFORE calling the LLM
    if not outfit or not outfit.strip():
        return "Can't generate a fit card without an outfit suggestion."

    # Pull the key details from the listing for the caption
    title    = new_item.get("title", "this thrifted find")
    price    = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift app")

    prompt = f"""
You are writing an Instagram/TikTok OOTD caption for someone who just thrifted this item:

Item: {title}
Price: ${price}
Platform: {platform}

Outfit they're wearing it with:
{outfit}

Write a 2–4 sentence caption that:
- Sounds like a real person posting their outfit, NOT a brand or product description
- Mentions the item name, price, and platform naturally (once each)
- Captures the specific vibe of this outfit
- Uses casual first-person voice (lowercase is fine, emojis are fine)
- Feels different and specific — not generic "thrift is sustainable" content

Return ONLY the caption text. No intro, no quotes around it.
""".strip()

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=150,
        )
        result = response.choices[0].message.content.strip()

        if not result:
            return "Can't generate a fit card without an outfit suggestion."

        return result

    except Exception as e:
        return f"Couldn't generate a fit card right now — try again. (Error: {e})"

