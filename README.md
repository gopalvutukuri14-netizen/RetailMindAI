# RetailMind AI

**AI-powered retail product recommendation system** built with a multi-agent architecture, semantic search, and real customer sentiment analysis.

RetailMind AI takes a natural-language shopping query (e.g. *"Best Samsung phone under 15000 with good camera"*), runs it through a pipeline of 7 specialized AI agents orchestrated by LangGraph, and returns ranked product recommendations with transparent explanations grounded in real Amazon review data.

The system supports **conversational context** — follow-up queries like *"Compare the top 2"* reference previous results, and non-product queries like *"hello"* or *"bye"* are handled conversationally without triggering the product pipeline.

---

## Architecture

```
User Query + Profile + Previous Products (context)
        |
        v
 +-----------------------+
 | Query Understanding   |   Parses intent, budget, brand, specs, quality tags
 +-----------------------+
        |
        v
 +------ Router --------+   Intent-based conditional routing
 |         |            |
 |  product |  follow-up |  general
 |  _recom  |  /compare  |  _question
 |         |            |
 v         v            v
Full     Context     General
Pipeline Response    Response
 |
 +----+----+
 |         |
 v         v
+----------+ +--------+
| Retrieval| | Memory |     Parallel: semantic search + user preference lookup
+----------+ +--------+
 |         |
 +----+----+
      |
      v
 +---------+
 | Ranking |               Scores by similarity, spec match, sentiment,
 +---------+               aspect alignment, memory alignment
      |
 +----+----+
 |         |
 v         v
+-----+  +----------+
| XAI |  | Follow-up|      Parallel: explanations + next-step suggestions
+-----+  +----------+
 |         |
 +----+----+
      |
      v
 +-----------+
 | Response  |              Synthesizes final user-facing response
 +-----------+
      |
      v
 JSON Response
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **LLM** | Google Gemini (gemini-3.5-flash-lite) |
| **Orchestration** | LangGraph (StateGraph) |
| **Embeddings** | BGE-M3 (BAAI/bge-m3) |
| **Vector Store** | ChromaDB |
| **Sentiment** | VADER + aspect-level precomputed scores |
| **User Memory** | SQLite |
| **Backend** | FastAPI |
| **Frontend** | React + Vite |
| **Language** | Python 3.10 / JavaScript |

## Project Structure

```
RetailMindAI/
├── backend/
│   ├── main.py                          # FastAPI app with /recommend endpoint
│   ├── orchestrator/                    # LangGraph pipeline
│   │   ├── state.py                     # Shared pipeline state (TypedDict)
│   │   ├── nodes.py                     # Agent wrapper functions
│   │   └── graph.py                     # StateGraph wiring + run_pipeline()
│   ├── Agents/
│   │   ├── query_understanding/         # Parses user query → structured fields
│   │   ├── retrieval/                   # Semantic search over ChromaDB
│   │   ├── memory/                      # User preference profiles (SQLite)
│   │   ├── ranking/                     # Multi-signal scoring & ranking
│   │   ├── xai/                         # Explainable AI — why each product ranked
│   │   ├── follow_up/                   # Suggests next questions/actions
│   │   └── response/                    # Final response synthesis
│   └── pipeline/
│       ├── retrieval.py                 # ProductRetriever (BGE-M3 + ChromaDB)
│       ├── clean_products.py            # Data cleaning
│       ├── sentiment_analysis.py        # Review sentiment scoring
│       ├── aspect_sentiment.py          # Per-aspect sentiment extraction
│       ├── product_sentiment.py         # Product-level sentiment aggregation
│       ├── products_for_embedding.py    # Embedding text preparation
│       ├── generate_embeddings.py       # BGE-M3 embedding generation
│       └── load_chromadb.py             # Load embeddings into ChromaDB
├── frontend/
│   └── src/
│       ├── App.jsx                      # Main chat UI shell
│       ├── App.css                      # Dark glassmorphism design system
│       ├── api/recommend.js             # API client
│       └── components/
│           ├── ChatWindow.jsx           # Message list with auto-scroll
│           ├── ChatInput.jsx            # Query input bar
│           ├── MessageBubble.jsx        # User/bot message rendering
│           ├── ProductCard.jsx          # Recommendation card
│           ├── ProfileSelector.jsx      # User persona dropdown
│           ├── FollowUpChips.jsx        # Clickable follow-up suggestions
│           └── TypingIndicator.jsx      # Loading animation
├── data/
│   ├── chromadb/                        # ChromaDB persistent storage (5,096 products)
│   ├── memory.db                        # SQLite user profiles
│   ├── products.csv                     # Raw product metadata
│   ├── products_clean.csv               # Cleaned product data
│   ├── reviews.csv                      # Raw reviews
│   ├── reviews_sentiment.csv            # Reviews with sentiment scores
│   ├── product_sentiment.csv            # Aggregated product sentiment
│   ├── product_aspect_sentiment.csv     # Per-aspect sentiment scores
│   ├── products_for_embedding.csv       # Embedding-ready text
│   ├── product_embeddings.npy           # BGE-M3 dense vectors
│   └── product_embedding_asins.csv      # ASIN index for embeddings
└── notebooks/                           # Jupyter notebooks for exploration
```

## Data Pipeline

```
Amazon Cell Phones & Accessories dataset
        |
        v
products.csv + reviews.csv                    (Raw data)
        |
        v
products_clean.csv                             (Cleaned, structured specs extracted)
        |
        v
reviews_sentiment.csv                          (VADER sentiment per review)
        |
        v
product_sentiment.csv                          (Aggregated per product)
product_aspect_sentiment.csv                   (Camera/battery/display/performance/value)
        |
        v
products_for_embedding.csv                     (Merged text for BGE-M3)
        |
        v
product_embeddings.npy                         (BGE-M3 dense vectors)
        |
        v
ChromaDB (5,096 products with embeddings + metadata + sentiment)
```

## Agents

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Query Understanding** | Parse natural language into structured fields | Raw query string | Intent, budget, brand, specs, quality tags |
| **Retrieval** | Semantic search + metadata filtering | Parsed query | Top-K candidate products with specs & sentiment |
| **Memory** | Load user preference profile | User ID | Brand prefs, budget, quality tags |
| **Ranking** | Multi-signal scoring (5 weighted signals) | Candidates + profile | Ranked products with score breakdowns |
| **XAI** | Generate human-readable explanations | Query + rankings | Per-product explanations + key factors |
| **Follow-up** | Suggest next actions | Query + rankings | 2-4 contextual suggestions |
| **Response** | Synthesize final output | All upstream outputs | Summary + product cards + follow-ups |

### Intent-Based Routing

After Query Understanding parses the intent and category, the orchestrator routes to one of four paths:

| Condition | Route | What Happens |
|-----------|-------|-------------|
| Product query (in-scope) | **Full Pipeline** | Retrieval + Memory → Ranking → XAI + Follow-up → Response |
| `comparison` / `follow_up` (with context) | **Context Response** | Uses previously shown products to compare or answer — skips retrieval/ranking |
| `general_question` | **General Response** | Conversational reply (greetings, goodbyes, general knowledge) — no products |
| Out-of-scope category (watches, laptops, etc.) | **Out of Scope** | Polite redirect explaining we only cover cell phones — no products |

This means "Compare the top 2" actually compares the products just shown, "bye" gets a friendly goodbye, "i want watches under 1000" gets a polite redirect, and new phone queries still run the full pipeline.

### Ranking Signals (Weighted)

| Signal | Weight | Source |
|--------|--------|--------|
| Semantic similarity | 0.30 | BGE-M3 embedding distance |
| Spec match | 0.20 | RAM/storage/camera/battery vs user requirements |
| Sentiment | 0.15 | Aggregated review sentiment score |
| Aspect alignment | 0.25 | Aspect-level sentiment for user's quality tags |
| Memory alignment | 0.10 | Match against stored user preferences |

## User Profiles (Demo)

The system includes 3 pre-seeded user profiles for demonstrating personalization:

| Profile ID | Behavior |
|------------|----------|
| `anonymous` | No personalization (default) |
| `budget_conscious` | Prefers phones under Rs.10,000 |
| `camera_focused` | Prioritizes good camera quality |
| `samsung_loyalist` | Prefers Samsung brand |

## Setup & Running

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd RetailMindAI

python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux
```

### 2. Install Python dependencies

```bash
pip install fastapi uvicorn python-dotenv google-genai pydantic
pip install chromadb FlagEmbedding numpy pandas
pip install vaderSentiment
pip install langgraph
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_key_here
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

### 5. Run the application

```bash
# Terminal 1 — Backend (from project root)
uvicorn backend.main:app --reload

# Terminal 2 — Frontend
cd frontend
npm run dev
```

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/health` | GET | Service health status |
| `/understand` | POST | Debug: parse query only |
| `/recommend` | POST | **Full pipeline** — returns ranked recommendations |

### Example: Product Recommendation

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Best Samsung phone under 15000 with good camera",
    "user_id": "camera_focused",
    "top_k": 5
  }'
```

### Example: Follow-up with Context

```bash
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare the top 2 options",
    "user_id": "camera_focused",
    "previous_products": [
      {"asin": "B00...", "title": "Samsung Galaxy A...", "brand": "Samsung", "price_inr": 12500},
      {"asin": "B01...", "title": "Samsung Galaxy M...", "brand": "Samsung", "price_inr": 14000}
    ]
  }'
```

### Example Response

```json
{
  "summary": "Here are the best Samsung phone options under 15000...",
  "recommendations": [
    {
      "asin": "B00...",
      "title": "Samsung Galaxy...",
      "brand": "Samsung",
      "price_inr": 12500.0,
      "explanation": "This Samsung phone matches your budget with strong camera reviews.",
      "key_factors": ["Within budget", "Strong camera sentiment", "Samsung brand match"]
    }
  ],
  "additional_information": "All products are from Samsung and priced under 15000.",
  "follow_up_suggestions": [
    "Want me to compare the top 2 options?",
    "Would you like to see phones with more storage?"
  ]
}
```

## License

This project is for academic/research purposes.
