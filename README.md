# ⚡ Research Digest Agent

![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-92%25-green)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Less noise. More signal.

An autonomous agent that ingests multiple research sources, extracts key claims, removes redundancy, and produces a structured evidence-backed digest.

---

## Quickstart

```bash
# Install dependencies
pip install requests beautifulsoup4 scikit-learn

# Run the agent
python main.py

# Run tests (no extra installs needed)
python -m tests.test_agent
```

> **Note:** Always run from inside the `research-digest-agent/` directory.

Output files are written to the `output/` folder:
- `output/digest.md` — structured digest grouped by theme
- `output/sources.json` — per-source claims with evidence and confidence scores

---

## How the Agent Processes Sources (Step by Step)

### Step 1 — Content Ingestion (`agent/ingestion.py`)
The agent accepts a list of URLs or local file paths. For each input:
- **URLs** are fetched via `requests` with a browser-like User-Agent. Non-200 responses, non-HTML content, and network failures are all skipped gracefully. HTML is parsed with BeautifulSoup and `<p>` tags are extracted as content.
- **Files** are read from disk with UTF-8 encoding.

Content below `MIN_CONTENT_LENGTH` (200 chars) or above `MAX_CONTENT_LENGTH` (100,000 chars) is discarded. Duplicate URLs are tracked via a `seen_sources` set and skipped silently on re-submission.

### Step 2 — Cleaning (`agent/cleaning.py`)
Each source's raw text is normalized through a multi-step pipeline:
1. Whitespace collapsed to single spaces
2. Non-ASCII characters removed
3. Wikipedia footnote numbers (e.g. `13 14 In a 2022...`) stripped using regex
4. Inline citation brackets like `[13]` removed
5. Special symbols stripped, keeping alphanumerics and basic punctuation
6. Sentences shorter than 40 characters dropped
7. Boilerplate lines ("cookie", "privacy policy", "subscribe") filtered out

### Step 3 — Claim Extraction (`agent/claim_extractor.py`)
The `RuleBasedExtractor` scores each sentence using a multi-signal heuristic:

| Signal | Score |
|---|---|
| Contains percentage, dollar amount, or year | +1 per match |
| Contains a measurement (kWh, km, million, etc.) | +1 |
| Contains superlatives (largest, first, fastest) | +1 |
| Cites a study or report ("research shows", "data indicates") | +1 |
| Contains causal reasoning ("because", "due to", "therefore") | +1 |
| Comparative language ("more than", "higher than") | +0.5 |

Only sentences scoring ≥ 1.5 AND passing an informativeness check (word diversity ratio > 0.5, minimum 8 words) are kept as claims. The raw sentence is stored verbatim as the `evidence` field — no paraphrasing or inference. A `confidence` score (0.0–1.0) is derived by normalizing the total signal score.

### Step 4 — Deduplication (`agent/deduplicator.py`)
1. Claims are **bucketed by topic** (battery, emissions, cost, market, efficiency, general) using keyword matching — prevents cross-topic false positives and improves speed.
2. Within each bucket, claims are **TF-IDF vectorized** and pairwise **cosine similarity** is computed.
3. A **keyword overlap ratio** acts as a secondary signal for short claims where TF-IDF vectors are sparse.
4. Two claims merge into one group if `cosine_similarity ≥ 0.3` OR `keyword_overlap > 0.3`.
5. Before comparison, text is normalized: lowercased, numbers removed, stopwords stripped, synonyms collapsed ("cars" → "vehicle", "emissions" → "emission").

### Step 5 — Theme Assignment (`agent/grouper.py`)
Each group is assigned a human-readable theme label using the most frequent meaningful words (length > 5 chars) across all claims in the group, filtered through a custom stopword list and title-cased for readability.

### Step 6 — Output Generation (`agent/output.py`)
- **`digest.md`** — Markdown file with one section per theme. Each claim shows its text, verbatim evidence quote, confidence score, and source title with URL.
- **`sources.json`** — JSON keyed by source title, listing all claims per source with evidence and confidence score.

---

## How Claims Are Grounded

Every claim's `evidence` field stores the **exact original sentence** from the source — no paraphrasing, no inference, no invention. The extractor only surfaces sentences literally present in the fetched content. Source title and URL are always attached to each claim, making every assertion fully traceable back to its origin. The agent is explicitly designed to never fabricate facts.

---

## How Deduplication / Grouping Works

Deduplication runs in two stages:

**Stage 1 — Topic Bucketing:** Claims are pre-grouped by domain using keyword rules. This prevents semantically unrelated claims from being compared against each other, improving both precision and performance.

**Stage 2 — Similarity Comparison:** Within each bucket, TF-IDF cosine similarity is computed for every pair. A keyword overlap ratio provides a fallback for short claims where TF-IDF vectors are sparse. Claims merge if either metric crosses its threshold. All source IDs are tracked per group, so multi-source support for a claim is always preserved.

Text normalization before comparison includes lowercasing, number removal, punctuation stripping, stopword filtering, and synonym normalization — ensuring that surface differences in wording don't prevent semantically identical claims from being grouped.

---

## Limitation

The rule-based extractor relies on surface-level signals (numbers, keywords, sentence length) and cannot understand meaning. It may miss important qualitative claims that lack numeric evidence, and may occasionally surface sentences that look claim-like but carry little insight. A language model would be significantly more accurate at distinguishing genuine insights from background text.

---

## One Improvement With More Time

Replace `RuleBasedExtractor` with the `LLMExtractor` stub already present in `claim_extractor.py`. Each source would be passed to an LLM with a structured prompt asking for claims in JSON format, complete with an explicit confidence rationale and conflict flagging. This would handle nuanced qualitative insights, detect opposing viewpoints explicitly, and produce far fewer false positives — without requiring any changes to the rest of the pipeline, since the interface is already defined.

---

## Project Structure

```
research-digest-agent/
├── agent/
│   ├── claim_extractor.py   # Multi-signal claim scoring with confidence scores
│   ├── cleaning.py          # Text normalization, footnote removal, noise filtering
│   ├── deduplicator.py      # TF-IDF + keyword overlap deduplication
│   ├── grouper.py           # Theme label generation
│   ├── ingestion.py         # URL and file ingestion with full error handling
│   ├── output.py            # digest.md and sources.json generation
│   └── pipeline.py          # Orchestrates all 6 steps end-to-end
├── config/
│   └── settings.py          # Thresholds and feature flags
├── models/
│   └── schemas.py           # Source, Claim, ClaimGroup schemas
├── tests/
│   └── test_agent.py        # 18 tests using built-in unittest
├── output/
│   ├── digest.md            # Sample generated digest
│   └── sources.json         # Sample generated sources
├── main.py                  # Entry point
└── README.md
```

---

## Configuration (`config/settings.py`)

| Setting | Default | Description |
|---|---|---|
| `SIMILARITY_THRESHOLD` | `0.3` | Cosine similarity cutoff for deduplication |
| `MIN_CONTENT_LENGTH` | `200` | Minimum source length to process |
| `MAX_CONTENT_LENGTH` | `100000` | Max characters before truncation |
| `USE_LLM` | `False` | Toggle for future LLM-based extraction |

---

## Sample Topic

**AI Regulation & Policy** — 5 Wikipedia sources covering distinct angles of the debate:

| Source | Focus |
|---|---|
| [Regulation of artificial intelligence](https://en.wikipedia.org/wiki/Regulation_of_artificial_intelligence) | Global laws and policy frameworks |
| [AI safety](https://en.wikipedia.org/wiki/AI_safety) | Alignment, existential risk |
| [Algorithmic bias](https://en.wikipedia.org/wiki/Algorithmic_bias) | Fairness, discrimination in AI |
| [Artificial general intelligence](https://en.wikipedia.org/wiki/Artificial_general_intelligence) | AGI definitions and timelines |
| [Ethics of artificial intelligence](https://en.wikipedia.org/wiki/Ethics_of_artificial_intelligence) | Moral questions, governance |
