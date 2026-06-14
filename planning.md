# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It searches a second-hand item given by the user in the mock listing listings.json. The user provides the description, size and maximum price and returns a ranked list of possible matches.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Description of the second-hand item the user is looking for  (e.g., "vintage graphic tee"). This will be matched against title, description, style_tags, category, and brand fields.
- `size` (str): The size of the item the user is looking for (e.g., "M", "L/XL").
- `max_price` (float): The maximum price the user is willing to pay for the item.

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
Returns a list of matching listing objects, each dict contains  id, title, description, category, style_tags (list), size, condition, price (float), colors (list), brand, platform. Returns an empty list if nothing matches — never raises an exception.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the agent does not find any item matching the user's request, it informs the user explicity and suggests retrying with a looser size filter (retry logic stretch feature). If retry also fails, the agent asks the user to adjust their description or price range. The agent sets session["error"] to a message like: "No listings found for '[query]'. Try broadening your search — remove the size filter or increase your price range." The agent returns early and does NOT call suggest_outfit.

---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Given an item and a wardrobe, the tool suggests a combination of items to form 1 or 2 complete outfits using pieces the user already knows. 

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A listing dict — the item the user is considering buying. Used for its title, style_tags, colors, and category. 
- `wardrobe` (dict): a dictionary containing a combination of items that form a wardrobe. Each item has: name, category, colors, style_tags, notes.

**What it returns:**
<!-- Describe the return value -->
Returns a string with a suggested outfit combination, describing which wardrobe items pair well with the new item and why. Example: 'Pair this faded band tee with your wide-leg jeans and chunky sneakers for a 90s grunge look.'

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If there is not a good combination or there is not a wardrobe available to compare against, suggest_outfit explicitly explains the customer and suggests options based on general knowledge.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
It generates a short string in 2-4 sentences for the found outfit in Instagram/TickTock tone.


**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion string returned by suggest_outfit().
- `new_item` (dict): The listing dict for the item. Used for title, price, and platform.

**What it returns:**
<!-- Describe the return value -->
A fit_card which is a string composed of 2-4 sentences ready to use in socials like Instagram. It mentions the item name, price and platform once each in a natural way. It captures the outfit vibe in specific terms. If outfit is empty or made of spaces only, it returns an error string informing that it can't generate a fit card without an outfit suggestion.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
Guards against empty outfit string before calling the LLM. Returns a descriptive error message string instead of raising an exception.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
The agent runs a linear pipeline with one conditional branch:


Parse the user query to extract description, size, and max_price using regex patterns.
Call search_listings(description, size, max_price).
Branch: If search_results is empty → set session["error"] with a helpful message, return session early. Do NOT proceed.
If results exist → set session["selected_item"] = search_results[0] (top result by relevance score).
Call suggest_outfit(selected_item, wardrobe) → store in session["outfit_suggestion"].
Call create_fit_card(outfit_suggestion, selected_item) → store in session["fit_card"].
Return the completed session.


The agent does NOT call all three tools unconditionally — step 3 is the real branch point that changes behavior based on what search_listings returned.

---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
All state lives in a single `session` dict initialized by `_new_session()` in `agent.py`. Fields:

| Key | Set by | Used by |
|-----|--------|---------|
| `query` | `run_agent()` on init | reference only |
| `parsed` | query parser in step 2 | `search_listings` call |
| `search_results` | `search_listings` | step 3 branch check |
| `selected_item` | step 4 | `suggest_outfit`, `create_fit_card` |
| `wardrobe` | `run_agent()` on init | `suggest_outfit` |
| `outfit_suggestion` | `suggest_outfit` | `create_fit_card` |
| `fit_card` | `create_fit_card` | returned to UI |
| `error` | error branch | returned to UI |

No tool re-reads the original query or re-prompts the user — all inputs flow from the session dict.

---

## Error Handling

<!--For each tool, describe the specific failure mode you're handling and what the agent does in response.-->

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No results match the query | Sets `session["error"]`: "No listings found for '[query]'. Try removing the size filter or raising your price limit." Returns session early — `suggest_outfit` is never called. |
| `suggest_outfit` | Wardrobe is empty | LLM prompt switches to general styling advice: "No wardrobe items provided — here's how to style this piece in general..." Never returns empty string. |
| `create_fit_card` | `outfit` string is empty or whitespace | Returns error string immediately without calling the LLM: "Can't generate a fit card without an outfit suggestion." |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

```
User query (natural language)
        │
        ▼
  Query Parser (regex)
  → extracts: description, size, max_price
  → stores in session["parsed"]
        │
        ▼
  search_listings(description, size, max_price)
  → stores in session["search_results"]
        │
        ├── results == [] ──► session["error"] = "No listings found..."
        │                              │
        │                              ▼
        │                         return session  ◄─── early exit
        │
        │ results found
        ▼
  session["selected_item"] = results[0]
        │
        ▼
  suggest_outfit(selected_item, wardrobe)
  → stores in session["outfit_suggestion"]
        │
        ├── wardrobe empty ──► LLM uses general styling prompt (no crash)
        │
        ▼
  create_fit_card(outfit_suggestion, selected_item)
  → stores in session["fit_card"]
        │
        ├── outfit empty ──► returns error string (no LLM call, no crash)
        │
        ▼
  return session  ◄─── happy path exit
```

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
- **`search_listings`:** Give Claude the Tool 1 spec (inputs, return value, failure mode, fields to search against) and ask it to implement the function using `load_listings()`. Verify: does it filter by all 3 params? Does it score by keyword overlap across title + description + style_tags + category + brand? Does it return `[]` on no match without crashing? Test with 3 queries: one that returns results, one that returns empty, one that tests price filter.

- **`suggest_outfit`:** Give Claude the Tool 2 spec plus the wardrobe schema structure. Ask it to implement using Groq (`llama-3.3-70b-versatile`). Verify: does it handle empty wardrobe separately? Does it format wardrobe items into the prompt? Does it never return empty string?

- **`create_fit_card`:** Give Claude the Tool 3 spec and the style guidelines (casual voice, mention price/platform once, feel like OOTD post). Ask it to use higher temperature (0.9). Verify: does it guard against empty outfit? Does it vary across runs? Does it sound like a real caption?

**Milestone 4 — Planning loop and state management:**

- Give Claude the full Architecture diagram above + the Planning Loop section + the State Management table. Ask it to implement `run_agent()` in `agent.py` following the numbered steps. Verify: does it branch on empty search results? Does it store each result in the correct session key? Does it NOT call all three tools unconditionally?

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
Query parsing. Regex extracts: `description = "vintage graphic tee"`, `size = None` (not specified), `max_price = 30.0`. Stored in `session["parsed"]`.

**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
search_listings. Regex extracts: `description = "vintage graphic tee"`, `size = None` (not specified), `max_price = 30.0`. Stored in `session["parsed"]`.

**Step 3:**
<!-- Continue until the full interaction is complete -->
suggest_outfit. Called with `(selected_item, example_wardrobe)`. LLM receives the item details + wardrobe items formatted as a list. Returns: "Pair this faded band tee with your baggy dark-wash jeans and chunky white sneakers for a classic 90s grunge look. Roll the sleeves once and tuck the front corner slightly for shape." Stored in `session["outfit_suggestion"]`.

**Step 4:**
create_fit_card. Called with `(outfit_suggestion, selected_item)`. LLM generates a casual caption mentioning the item, price, and platform. Returns: "thrifted this faded band tee off depop for $22 and it was literally made for my wide-legs 🖤 full look in my stories". Stored in `session["fit_card"]`.

**Final output to user:**
<!-- What does the user actually see at the end? -->
Three panels in the Gradio UI populate:
-  Top listing found: item title, price, platform, condition, size
-  Outfit idea: the suggest_outfit string
-  Your fit card: the create_fit_card caption
