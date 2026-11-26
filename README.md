# PourSight: Conversational AI Analytics for Small Hospitality Businesses

[![Backend](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![LLM](https://img.shields.io/badge/LLM-Groq%20Llama%203.3%2070B-F55036)](https://console.groq.com/)
[![Database](https://img.shields.io/badge/Data-SQLite%20(read--only)-003B57?logo=sqlite)](https://www.sqlite.org/)
[![Frontend](https://img.shields.io/badge/UI-React%20%2B%20Vite%20%2B%20Recharts-61DAFB?logo=react)](https://vitejs.dev/)
[![Deploy](https://img.shields.io/badge/Hosting-Docker%20on%20Render-46E3B7?logo=render)](https://render.com/)

A conversational AI analytics assistant that lets a bar or restaurant manager ask plain-English questions about their sales, menu, stock and match-day trade, and get back a **grounded answer, a chart and a concrete recommendation**. A question is turned into a single read-only SQL query by an LLM (**Groq, Llama 3.3 70B**) forced into a structured tool call, executed behind a **three-layer SQL safety guard**, checked by a rules-based **recommendation playbook** and an optional **TF-IDF retrieval** step over menu/recipe docs, then summarised by a second LLM call whose every cited number is **mechanically verified** against the query result. A 20-case evaluation harness measures query correctness, numeric accuracy and hallucination rate.

Pilot case study: **The Arsenal Bar & Grill, Bindura, Zimbabwe** (dual-currency USD/ZWG, EcoCash mobile money, Arsenal FC match-day trade).

AIM 5012 – Foundations and Practice of Effective Coding with AI, Summer 2026. Team: Alwyn Munatsi, Erasmus Tsuro.

**Live demo:** https://poursight-vq95.onrender.com/ (free tier — the first request after idling may take a few seconds to wake up)

---

## 1. System Architecture & End-to-End Data Flow

### End-to-End Execution Flow
$$\text{Question} \xrightarrow{\text{LLM tool call}} \text{QueryPlan (SQL)} \xrightarrow{\text{3-layer guard}} \text{SQLite rows} \xrightarrow{\text{Playbook + Retrieval}} \text{Context} \xrightarrow{\text{LLM}} \text{AnswerPlan} \xrightarrow{\text{Grounding check}} \text{Answer + Chart}$$

1. **React chat UI:** The manager types a question; the frontend `POST`s it to `/api/ask`.
2. **Stage 1 – NL→SQL (`llm/nl_to_sql.py`):** The model is forced (`tool_choice`) to call `emit_query_plan`, returning a `QueryPlan`: intent, SQL, parameters, chart type and whether menu-doc retrieval is needed. The schema description and few-shot examples live in the system prompt.
3. **Query guard (`db/query_engine.py`):** The generated SQL is untrusted until it passes three independent checks (see Section 6) and is capped at 500 rows.
4. **Playbook (`playbook/rules.py`):** Fixed rules inspect the *shape* of the result rows and propose recommendations (low margins, low stock, match-day lift, best-seller concentration).
5. **Retrieval (`retrieval/embed_docs.py`):** If `needs_retrieval` is set, the top menu/recipe documents are pulled from a dependency-free TF-IDF index.
6. **Stage 2 – Answer generation (`llm/answer_gen.py`):** A second forced tool call returns an `AnswerPlan` with answer text, a non-blank recommendation and the list of values it cites.
7. **Grounding (`llm/grounding.py`):** Every cited value must appear in the query rows (2% numeric tolerance) or in the playbook/retrieved text; drift is logged.
8. **Chart builder (`api/chart_builder.py`):** Picks label/value columns and returns a bar, line, pie or single-value chart spec rendered by Recharts.

---

## 2. Infrastructure & Component Directory

| Component | Technology | Purpose / Function in Solution | Configuration & Security Details |
| :--- | :--- | :--- | :--- |
| **`app/main.py`** | FastAPI + Uvicorn | API entrypoint; also serves the built frontend | Mounts `frontend/dist` after API routes, only if it exists |
| **`app/api/routes.py`** | FastAPI router | `GET /api/health`, `POST /api/ask` | Returns 503 if `GROQ_API_KEY` is missing, 422 on bad plans/queries |
| **`app/llm/`** | OpenAI SDK → Groq | NL→SQL, answer generation, grounding | `base_url` override to `api.groq.com`; model `llama-3.3-70b-versatile` |
| **`app/db/`** | SQLite | Synthetic pilot dataset + safe query engine | Connection opened read-only; table/column/function whitelist |
| **`app/playbook/`** | Pure Python | Deterministic recommendation rules | Thresholds: margin < 45%, match-day lift ≥ 15%, top-item share ≥ 30% |
| **`app/retrieval/`** | TF-IDF + cosine similarity | Menu/recipe context for dish questions | No API key, network call or ML dependency |
| **`frontend/`** | React + Vite + Recharts | Chat UI with charts | Vite proxies `/api/*` to `:8000` in dev |
| **`backend/eval/`** | Python harness | 20 fixed QA cases with gold SQL | Writes `eval/report.md` |
| **`Dockerfile` / `render.yaml`** | Docker multi-stage, Render | Single-service deploy | `GROQ_API_KEY` supplied at runtime, never baked into the image |

---

## 3. Engineering Decisions (Why It's Built This Way)

| Concern | Common Approach | This Implementation | Technical Justification |
| :--- | :--- | :--- | :--- |
| **LLM output format** | Free-text completion parsed with regex | **Forced tool calls → Pydantic models** (`QueryPlan`, `AnswerPlan`) | The response is always a validated JSON shape; a missing tool call or bad shape is a clean 422, not a crash. |
| **SQL safety** | Trust the model / prompt it to be careful | **Text check + SQLite authorizer whitelist + read-only connection** | Any one layer can fail without letting a write or an off-schema read through. |
| **Hallucinations** | Hope the model copies numbers correctly | **Mechanical grounding check** on every cited value | Numbers must match the rows (2% tolerance) or trusted prose; measured at 0% ungrounded in eval. |
| **Recommendations** | Let the model improvise | **Deterministic playbook first**, model fills the rest | Business rules are explainable and testable; every answer still gets a recommendation. |
| **Retrieval** | Neural embeddings + vector DB | **TF-IDF over ~17 docs** | The corpus is tiny and static; `search()` is the only interface, so it can be swapped later. |
| **LLM provider** | OpenAI/Anthropic directly | **Groq via the OpenAI SDK** | OpenAI-compatible API, fast cheap inference on open-weight models. |
| **Evaluation** | Match generated SQL text | **Compare query *results* against hand-written `gold_sql`** | Two different `SELECT`s can both be right if they return the same data. |
| **Deployment** | Separate frontend host + CORS | **One Docker image, one origin** | FastAPI serves the static build; dataset and corpus are regenerated at build time, so no volume is needed. |

---

## 4. Phase 1: Synthetic Pilot Dataset (SQLite)

`backend/app/db/seed.py` generates a deterministic dataset using distributions modelled on public restaurant POS data, with Arsenal Bar & Grill specifics layered in.

| Table | Contents |
| :--- | :--- |
| `menu_items` | Name, category (Beer, Cider, Spirits, Soft Drink, Starter, Grill, Sadza & Sides, Dessert), USD price and cost |
| `ingredients` | Unit, unit cost, stock on hand, reorder level |
| `recipe_items` | Ingredient quantities per serving (links menu ↔ ingredients) |
| `orders` | Timestamp, weekday/weekend, match-day flag, payment method (`cash_usd`, `cash_zwg`, `ecocash`, `card`), currency, table |
| `order_items` | Line items with unit price and line total in USD |
| `fx_rates` | Illustrative daily USD → ZWG (Zimbabwe Gold) rate |
| `match_days` | Illustrative Arsenal FC fixture calendar |

```bash
cd backend
python -m app.db.seed
```

---

## 5. Phase 2: Natural Language → SQL

The model sees the schema (with join and aggregation hints such as "sum `line_total_usd` per order before averaging") plus few-shot examples, and must reply through the `emit_query_plan` tool:

```json
{
  "intent": "Menu items ranked by lowest profit margin",
  "sql": "SELECT name AS item_name, price_usd, cost_usd, ROUND((price_usd - cost_usd) / price_usd * 100, 1) AS margin_pct FROM menu_items ORDER BY margin_pct ASC LIMIT 5",
  "params": [],
  "chart_type": "bar",
  "needs_retrieval": false
}
```

Relative dates ("last weekend", "yesterday") are resolved against a reference date passed as a bound parameter.

---

## 6. Phase 3: Three-Layer SQL Safety Guard

`run_query()` is the **only** path by which generated SQL can touch the database:

1. **Text-level check:** a single statement starting with `SELECT` or `WITH`; no `;`-chained statements.
2. **SQLite authorizer:** as the statement compiles, every table, column and function is checked against `ALLOWED_TABLES` and `ALLOWED_FUNCTIONS`; anything else is denied.
3. **Read-only connection:** the database is opened read-only at the SQLite level, so writes fail even if layers 1 and 2 were bypassed.

```python
def _check_single_read_statement(sql: str) -> str:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped:
        raise QueryValidationError("Empty query.")
    if ";" in stripped:
        raise QueryValidationError("Only a single statement is allowed.")
    first_word = stripped.split(None, 1)[0].lower()
    if first_word not in ("select", "with"):
        raise QueryValidationError("Only SELECT (or SELECT via WITH) statements are allowed.")
    return stripped
```

Results are capped at `MAX_ROWS = 500` and flagged as `truncated` when cut.

---

## 7. Phase 4: Playbook, Retrieval & Grounded Answers

### Recommendation playbook
| Rule | Fires when | Example recommendation |
| :--- | :--- | :--- |
| `low_margin_items` | A row's margin is below **45%** | Consider a small price increase or a cheaper supplier for the lowest-margin item |
| `low_stock_ingredients` | Stock on hand is at or below the reorder level | Place a restock order for the listed ingredients soon |
| `match_day_lift` | Match days lift the metric by at least **15%** | Schedule beer stock and extra staff ahead of Arsenal fixtures |
| `concentrated_best_sellers` | The top item is **30%+** of the units shown | Make sure that item never runs out of stock |

### Retrieval
`backend/app/retrieval/menu_docs/*.md` (one per dish) are built from the same recipe data used to seed the database plus hand-written descriptions. Regenerate with `python -m app.retrieval.build_docs`.

### Grounding
`grounding.py` treats two sources as legitimate: the structured query rows (numeric tolerance 2% relative / 0.01 absolute, so `40`, `"40.0%"` and `"$40.00"` match) and trusted prose (playbook text and retrieved docs, matched as substrings).

---

## 8. Phase 5: Chat UI & Charts

The React frontend (`QuestionForm`, `MessageBubble`, `ChartView`) shows each answer with its recommendation and a Recharts visual chosen from the plan's `chart_type` (`bar`, `line`, `pie`, `single_value`). The `/api/ask` response also returns the SQL, intent, row count and truncation flag for transparency.

---

## 9. Evaluation Harness & Results

`backend/eval/cases.jsonl` holds 20 fixed questions, each with a trusted `gold_sql` returning a single `gold_value` column.

| Metric | What it measures | Latest result |
| :--- | :--- | :--- |
| **Query correctness** | Does the generated SQL retrieve the right data? | **95%** |
| **Numeric accuracy** | Does the final answer state the right number/fact? | **95%** |
| **Hallucination rate** | Share of cited values not found in the query result | **0%** (0/44 citations) |
| **Recommendation coverage** | Share of completed cases with a non-blank recommendation | **100%** |

19 of 20 cases completed. The one error (`retrieval_dish_price`) was a SQL error in the model's own query, caught and reported cleanly rather than crashing the run. See `backend/eval/report.md` for the per-case table and `PROMPTS.md` for prompt versions and design rationale. Groq's free tier caps at 100K tokens/day, so budget for repeated full runs.

```bash
cd backend
python -m eval.run_eval
```

---

## 10. Repository Structure

```text
poursight/
├── README.md
├── PROMPTS.md                          <-- Prompt design notes and version history
├── SKILL.md                            <-- Reusable skill definition
├── Dockerfile                          <-- Multi-stage build (Node → Python)
├── render.yaml                         <-- Render blueprint (free web service)
├── .env.example
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py                     <-- FastAPI entrypoint + static frontend
│   │   ├── config.py
│   │   ├── api/routes.py               <-- /api/health, /api/ask
│   │   ├── api/chart_builder.py
│   │   ├── db/schema.sql               <-- SQLite schema
│   │   ├── db/seed.py                  <-- Synthetic dataset generator
│   │   ├── db/query_engine.py          <-- Three-layer SQL guard
│   │   ├── llm/nl_to_sql.py            <-- Stage 1: question → QueryPlan
│   │   ├── llm/answer_gen.py           <-- Stage 2: rows → AnswerPlan
│   │   ├── llm/grounding.py            <-- Cited-value verification
│   │   ├── llm/schemas.py              <-- Pydantic models
│   │   ├── playbook/rules.py           <-- Recommendation rules
│   │   └── retrieval/                  <-- TF-IDF index + menu_docs/*.md
│   ├── eval/                           <-- cases.jsonl, run_eval.py, report.md
│   └── tests/                          <-- pytest suite (API, guard, grounding, playbook, e2e, ...)
└── frontend/
    ├── vite.config.js
    └── src/                            <-- App.jsx, api.js, components/
```

---

## 11. Complete Step-by-Step Reproduction Guide

### Step 1: Configure the Environment
```bash
cp .env.example .env    # then set GROQ_API_KEY (and optionally GROQ_MODEL)
```

### Step 2: Run the Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m app.db.seed
python -m app.retrieval.build_docs
uvicorn app.main:app --reload
```
Health check: `GET http://localhost:8000/api/health`

### Step 3: Ask a Question
```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Which menu items have the lowest profit margin?"}'
```

### Step 4: Run the Frontend
```bash
cd frontend
npm install
npm run dev
```

### Step 5: Run Tests and the Evaluation
```bash
cd backend
pytest -q
python -m eval.run_eval
```

### Step 6: Deploy with Docker
```bash
docker build -t poursight .
docker run -p 8000:8000 --env-file .env poursight
```
On Render (or Railway/Fly.io), create a Docker web service from this repo, set `GROQ_API_KEY` in its environment, and the container listens on `$PORT` (default 8000).
