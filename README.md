# SmartPick

> **Find the right product for you.**

SmartPick is an AI-powered retail recommendation assistant built with a multi-agent architecture, semantic vector search, authentic Amazon product image retrieval, and customer sentiment analysis.

SmartPick takes natural-language shopping queries across **six major product categories** (e.g. *"Samsung phone under ₹30000 with 8GB RAM"*, *"Wireless Bluetooth headphones for gaming"*, *"Comfortable ergonomic office chair"*), orchestrates seven specialized AI agents via LangGraph, and delivers ranked recommendations with transparent explanations grounded in real customer reviews.

The system supports **conversational multi-turn context** — follow-up queries like *"Compare the top 2 options"* reference previously shown products, and non-product inquiries like greetings are handled conversationally without triggering the retrieval pipeline.

---

## Supported Product Categories

SmartPick supports six primary retail categories backed by ChromaDB semantic embeddings and Amazon catalog metadata:

1. **Cell Phones & Accessories**
2. **Electronics**
3. **Home & Kitchen**
4. **Clothing, Shoes & Jewelry**
5. **Office Products**
6. **Sports & Outdoors**

---

## System Architecture

```
User Query + Persona + Context (Previous Products)
                     |
                     v
       +----------------------------+
       |   Query Understanding      |   Extracts category, intent, budget,
       +----------------------------+   brand, specs & quality aspects
                     |
                     v
       +---------- Router ----------+   Intent & category conditional routing
       |             |              |           |
       | product     | follow-up    | general   | out of
       | _recom      | /compare     | _question | scope
       |             |              |           |
       v             v              v           v
  Full Pipeline    Context       General     Out of Scope
       |           Response      Response    Redirect
  +----+----+
  |         |
  v         v
+----------+ +--------+
| Retrieval| | Memory |     Parallel: BGE-M3 semantic search + SQLite profile lookup
+----------+ +--------+
  |         |
  +----+----+
       |
       v
  +---------+
  | Ranking |               5-signal weighted multi-objective scoring
  +---------+
       |
  +----+----+
  |         |
  v         v
+-----+  +----------+
| XAI |  | Follow-up|      Parallel: human-readable explanations + next steps
+-----+  +----------+
  |         |
  +----+----+
       |
       v
  +-----------+
  | Response  |              Synthesizes overview, resolves authentic image URLs,
  +-----------+              and formats null-safe INR pricing
       |
       v
  JSON Response / Frontend Recommendation Cards
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Google Gemini (`gemini-3.5-flash-lite`) with automated exponential backoff |
| **Agent Orchestration** | LangGraph (`StateGraph`) |
| **Dense Embeddings** | BAAI/bge-m3 (`FlagEmbedding`) |
| **Vector Store** | ChromaDB (`retail_products` collection) |
| **Catalog & Images** | Master Parquet catalog (`data/products_master.parquet`) + cached lookup |
| **Sentiment Analysis** | VADER + aspect-level customer sentiment extraction |
| **User Memory** | SQLite (`data/memory.db`) |
| **Backend** | FastAPI + Uvicorn + Pydantic v2 |
| **Frontend** | React 19 + Vite + Plus Jakarta Sans typography |
| **Styling** | Custom warm editorial CSS design system (ChatGPT-style scrolling layout) |

---

## The Seven Agents

| Agent | Purpose | Primary Inputs | Key Outputs |
|---|---|---|---|
| **1. Query Understanding** | Identifies query category, intent, budget constraints, specs, and aspects | Raw query string | Structured `QueryUnderstandingResult` |
| **2. Retrieval** | Executes semantic similarity search with category and metadata filtering | Query embeddings + filters | Candidate products with specs & review sentiments |
| **3. Memory** | Retrieves user persona preferences | User profile ID | Stored brand affinities, budget bounds, quality tags |
| **4. Ranking** | Multi-signal scoring combining 5 objective weights | Candidate products + profile | Ranked product list with granular subscores |
| **5. XAI (Explainable AI)** | Produces transparent "Why it matches" reasoning | Ranked products + query | Per-product explanations & key decision factors |
| **6. Follow-up** | Anticipates relevant subsequent user questions | Query context + recommendations | Contextual follow-up suggestions |
| **7. Response** | Formats final user-facing response with authentic images | Upstream agent outputs | Overview summary, cards, comparisons & next steps |

### Intent-Based Routing

* **Product Recommendation (`product_recommendation`)**: Runs the full 7-agent pipeline.
* **Follow-up / Comparison (`follow_up`, `comparison`)**: Routes directly to `Context Response` to compare or refine the previously recommended products without re-running retrieval.
* **General Question (`general_question`)**: Returns a conversational greeting or general shopping guidance.
* **Out of Scope (`out_of_scope`)**: Explains domain boundaries and redirects the user to supported categories.

### Ranking Signal Weights

| Signal | Weight | Description |
|---|---|---|
| **Semantic Similarity** | `0.30` | BGE-M3 dense vector cosine similarity |
| **Aspect Alignment** | `0.25` | Matches requested quality aspects to review sentiment |
| **Spec Match** | `0.20` | Verifies hardware/feature constraints (RAM, storage, materials, size) |
| **Sentiment Score** | `0.15` | Overall aggregated positive review sentiment |
| **Memory Alignment** | `0.10` | Preference alignment with user persona |

---

## Project Structure

```
RetailMindAI/
├── backend/
│   ├── main.py                          # FastAPI application & REST endpoints
│   ├── orchestrator/                    # LangGraph orchestration state machine
│   │   ├── graph.py                     # StateGraph compilation & run_pipeline()
│   │   ├── nodes.py                     # Agent wrappers & routing logic
│   │   └── state.py                     # Shared pipeline state schema
│   ├── Agents/                          # Seven specialized AI agents
│   │   ├── query_understanding/         # Category & constraint extraction
│   │   ├── retrieval/                   # ChromaDB semantic search
│   │   ├── memory/                      # SQLite persona management
│   │   ├── ranking/                     # Multi-signal scoring
│   │   ├── xai/                         # Explainable recommendation reasoning
│   │   ├── follow_up/                   # Contextual follow-up actions
│   │   ├── response/                    # Final response synthesis & image binding
│   │   └── gemini_retry.py              # Robust API retry handler
│   └── pipeline/
│       ├── product_images.py            # High-performance Parquet image lookup
│       ├── retrieval.py                 # ProductRetriever class
│       └── sentiment_analysis.py        # Review sentiment processing
├── frontend/
│   ├── index.html                       # HTML entry point with SmartPick favicon & typography
│   ├── src/
│   │   ├── App.jsx                      # ChatGPT-style full-viewport app layout
│   │   ├── App.css                      # Warm editorial design system tokens
│   │   ├── api/recommend.js             # FastAPI frontend client
│   │   └── components/
│   │       ├── CategoryBar.jsx          # 6-category horizontal navigation pills
│   │       ├── ChatInput.jsx            # Multi-category anchored search composer
│   │       ├── ChatWindow.jsx           # Clean conversation thread with start-anchored scroll
│   │       ├── MessageBubble.jsx        # Recommendation overview & cards layout
│   │       ├── ProductCard.jsx          # Circular rank badge (#1–#5), 150px photo, price & tags
│   │       ├── ProfileSelector.jsx      # Multi-category shopping persona dropdown
│   │       └── FollowUpChips.jsx        # Clickable follow-up prompt pills
│   └── public/
│       └── favicon.svg                  # SmartPick official SVG brand favicon
├── data/
│   ├── chromadb/                        # ChromaDB vector index (250,000+ products)
│   ├── products_master.parquet          # Master catalog with authentic image URLs
│   └── memory.db                        # SQLite user profile storage
├── tests/
│   ├── test_all_categories.py           # Multi-category LangGraph pipeline evaluation
│   ├── test_fastapi_endpoints.py        # FastAPI live API regression suite
│   ├── test_product_images.py           # Image URL resolution & fallback tests
│   └── verify_fastapi_live.py           # Live endpoint smoke test
└── requirements.txt                     # Python backend dependencies
```

---

## Setup & Installation

### Prerequisites

* **Python 3.10+**
* **Node.js 18+** & **npm**
* **Google Gemini API Key**

### 1. Clone & Set Up Python Environment

```bash
git clone <repo-url>
cd RetailMindAI

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

---

## Running the Application

### 1. Start the Backend Server

```bash
# From project root
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

* Backend API: `http://127.0.0.1:8000`
* Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`

### 2. Start the Frontend Development Server

```bash
# In a separate terminal
cd frontend
npm run dev
```

* Web Application: `http://127.0.0.1:5173`

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Root status endpoint (`{"message": "SmartPick backend is running"}`) |
| `/health` | `GET` | Health check with supported categories count (`6`) |
| `/understand` | `POST` | Inspect Query Understanding agent output for debugging |
| `/recommend` | `POST` | Primary recommendation endpoint executing the full pipeline |

### Example Request: Product Recommendation

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Samsung phone under ₹30000 with 8GB RAM",
    "user_id": "budget_conscious",
    "top_k": 5
  }'
```

### Example Request: Follow-up Comparison with Context

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare the top 2 options",
    "user_id": "budget_conscious",
    "previous_products": [
      {
        "asin": "B07RPHM14M",
        "title": "Galaxy S10 5G 8GB RAM 256GB",
        "brand": "SAMSUNG",
        "price_inr": 28687.0
      },
      {
        "asin": "B08N5WRWNW",
        "title": "Galaxy A51 8GB RAM 128GB",
        "brand": "SAMSUNG",
        "price_inr": 22499.0
      }
    ]
  }'
```

### Example Structured Response

```json
{
  "summary": "Here are the top Samsung phones under ₹30,000 matching your 8GB RAM requirement.",
  "recommendations": [
    {
      "asin": "B07RPHM14M",
      "title": "Samsung Galaxy S10 5G Enabled 6.7in 8GB+256GB",
      "brand": "SAMSUNG",
      "price_inr": 28687.12,
      "image_url": "https://m.media-amazon.com/images/I/41lVosxv3pL._AC_.jpg",
      "explanation": "Matches your 8GB RAM specification and falls within your ₹30,000 budget with strong customer sentiment.",
      "key_factors": ["8GB RAM verified", "Under ₹30,000", "High camera sentiment"]
    }
  ],
  "additional_information": "Both models include 8GB RAM and support fast charging.",
  "follow_up_suggestions": [
    "Compare the battery life of the top 2 options",
    "Would you prefer an AMOLED display?"
  ]
}
```

---

## Testing & Quality Verification

Run the comprehensive automated test suite (103 unit and integration tests):

```bash
# Run complete test suite
pytest tests/

# Test live FastAPI server integration
python -m tests.verify_fastapi_live

# Test multi-category evaluation queries
python -m tests.test_all_categories

# Build production frontend bundle
cd frontend && npm run build
```

---

## User Personas (Personalization Demo)

SmartPick includes pre-seeded user preference profiles stored in SQLite (`data/memory.db`):

| Persona ID | Label | Behavioral Bias |
|---|---|---|
| `anonymous` | **Standard Search** | Neutral baseline (no personalization applied) |
| `budget_conscious` | **Budget Conscious** | Strong preference for maximum value and lower price tiers |
| `camera_focused` | **Quality & Optics** | Prioritizes build quality, premium optics, and top sentiment |
| `samsung_loyalist` | **Brand Loyalist** | Prioritizes preferred brand affinity |

---

## License

This project is developed for educational, academic, and research purposes.
