# SmartPick

> **Find the right product for you.**

SmartPick is an Agentic Retail Recommendation System with Explainable AI (XAI) built with a multi-agent architecture, semantic vector search, authentic Amazon product image retrieval, customer sentiment analysis, user-isolated dynamic memory, and structured side-by-side product comparisons.

SmartPick processes natural-language shopping queries across **six major product categories** (e.g. *"Samsung phone under ₹30000 with 8GB RAM"*, *"Wireless Bluetooth headphones for gaming"*, *"Comfortable ergonomic office chair"*), orchestrates seven specialized AI agents via LangGraph, and delivers ranked recommendations with transparent explanations grounded in real customer reviews.

The system supports **conversational multi-turn context** — follow-up queries like *"Compare the top 2 options"* reference previously recommended products, and non-product inquiries like greetings or out-of-scope requests are handled conversationally without triggering the retrieval pipeline.

---

## Key Features

- **7-Agent Orchestration via LangGraph**: Specialized agents for Query Understanding, Retrieval, Memory, Ranking, Explainability (XAIAgent), Follow-up, and Response.
- **Dynamic Category Filtering & Example Queries**: Seven interactive category buttons (`All Categories` + 6 product categories). Selecting a category updates example queries dynamically without triggering unwanted searches, and attaches category context when searching.
- **Structured Side-by-Side Product Comparison**: Compare recommended items side-by-side via conversational queries or the interactive **"Compare Top 2 Products"** button, complete with two product cards, category-adapted specification tables, honest missing-value fallbacks (`"Price unavailable"`, `"Not available in catalog"`), and a trade-off conclusion verdict.
- **Performance Optimized**: Sub-second ChromaDB retrieval (optimized title scanning) and streamlined Response Agent synthesis reduce sequential agent time from ~39s to ~6.4s (83.6% reduction).
- **User Authentication & Cloud Database**: Neon PostgreSQL with JWT Bearer authentication, Argon2id password hashing, user-isolated preferences, and Brevo transactional email OTP verification.
- **Explainable Recommendations (XAI)**: Every recommendation provides a clear "Why it matches" explanation grounded in customer review sentiment and extracted specifications.

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
User Query + User ID / Token + Context (Previous Products) + Category Context
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
                 +----+----+      (Structured
                 |         |       Comparison)
                 v         v
               +----+   +------+
               |Retr|   |Memory|   Parallel: BGE-M3 semantic search + Neon DB profile
               +----+   +------+
                 |         |
                 +----+----+
                      |
                      v
                 +---------+
                 | Ranking |       5-signal weighted multi-objective scoring
                 +---------+
                      |
                 +----+----+
                 |         |
                 v         v
               +-----+  +----------+
               | XAI |  | Follow-up|   Concurrent: explanations + proactive next steps
               +-----+  +----------+
                 |         |
                 +----+----+
                      |
                      v
                 +-----------+
                 | Response  |     Synthesizes overview, resolves authentic image URLs,
                 +-----------+     formats INR pricing & side-by-side comparison tables
                      |
                      v
        JSON Response / Frontend Recommendation Cards & Comparison Table
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Google Gemini (`gemini-2.5-flash` / `gemini-3.5-flash-lite`) with automated exponential backoff |
| **Agent Orchestration** | LangGraph (`StateGraph`) |
| **Dense Embeddings** | BAAI/bge-m3 (`FlagEmbedding`) |
| **Vector Store** | ChromaDB (`retail_products` collection, 250,000+ products) |
| **Cloud Database** | Neon PostgreSQL (`users`, `user_preferences`, `conversation_memory`, `otp_challenges`) |
| **Authentication & Email** | JWT (HS256) + Argon2id + Brevo Transactional Email API (6-digit OTP verification) |
| **Catalog & Images** | Master Parquet catalog (`data/products_master.parquet`) + cached URL lookup |
| **Sentiment Analysis** | VADER + aspect-level customer sentiment extraction |
| **Backend** | Python + FastAPI + Uvicorn + Pydantic v2 + SQLAlchemy |
| **Frontend** | React 19 + Vite + Plus Jakarta Sans typography |
| **Styling** | Custom warm editorial CSS design system (responsive cards, comparison tables, category chips) |

---

## The Seven Agents

| Agent | Purpose | Primary Inputs | Key Outputs |
|---|---|---|---|
| **1. Query Understanding** | Identifies query category, intent, budget constraints, specs, and aspects | Raw query string + category | Structured `QueryUnderstandingResult` |
| **2. Retrieval** | Executes semantic similarity search with category and metadata filtering | Query embeddings + filters | Candidate products with specs & review sentiments |
| **3. Memory** | Retrieves user preferences and dynamic interaction history | User profile / JWT ID | Stored brand affinities, budget bounds, quality tags |
| **4. Ranking** | Multi-signal scoring combining 5 objective weights | Candidate products + profile | Ranked product list with granular subscores |
| **5. XAI (Explainable AI)** | Produces transparent "Why it matches" reasoning | Ranked products + query | Per-product explanations & key decision factors |
| **6. Follow-up** | Anticipates relevant subsequent user questions | Query context + recommendations | Contextual follow-up suggestions |
| **7. Response** | Formats final user-facing response with images & comparisons | Upstream agent outputs | Overview summary, cards, comparison table & next steps |

### Intent-Based Routing

* **Product Recommendation (`product_recommendation`)**: Runs the full 7-agent pipeline.
* **Follow-up / Comparison (`follow_up`, `comparison`)**: Routes to `Context Response` to compare or refine the previously recommended products with structured side-by-side comparison tables without re-running retrieval.
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

## Latency Benchmark & Performance Optimization

To deliver real-time recommendations, key bottlenecks were measured and eliminated:

1. **ChromaDB SQLite Table Scan Fixed**: Constrained `collection.get` calls in title search to `metadatas` only (omitting large `documents`), added upper-bound scan thresholds (1,000 items), and lowered title fetch limits, dropping retrieval time from **>40s down to 0.38s**.
2. **Streamlined Response Generation**: Replaced full JSON schema re-generation with a lightweight synthesis schema (`ResponseSynthesis`), dropping Response Agent time from **10.65s to 1.02s** while deterministically assembling the final response.
3. **Concurrent Execution**: Pre-triggered Follow-up Agent concurrently with XAI Agent in a thread pool.

| Component / Stage | Baseline Latency | Optimized Latency | Improvement |
| :--- | :--- | :--- | :--- |
| **ChromaDB Retrieval** | ~40.0+ s | **0.38 s** | **99.0% reduction** |
| **Response Agent** | 10.65 s | **1.02 s** | **90.4% reduction** |
| **Follow-up Agent** | 1.80 s | Concurrent with XAI | **0.00 s added** |
| **Sequential Stages Sum** | 38.95 s | **6.38 s** | **83.6% reduction** |
| **End-to-End Pipeline (Cold Start)** | ~79.79 s | **22.65 s** | **71.6% reduction** |
| **End-to-End Pipeline (Warm)** | ~50.00 s | **6.40 s** | **87.2% reduction** |

---

## Project Structure

```
SmartPick/
├── backend/
│   ├── main.py                          # FastAPI application & REST endpoints
│   ├── auth/                            # Authentication & email verification
│   │   ├── router.py                    # Signup, login, OTP verify, password reset
│   │   ├── dependencies.py              # JWT bearer token dependency (current_user)
│   │   ├── email_service.py             # Brevo transactional email sender
│   │   ├── schemas.py                   # Pydantic auth schemas
│   │   └── security.py                  # Argon2id hashing & JWT token management
│   ├── database/                        # Database models & sessions
│   │   ├── models.py                    # User, OTPChallenge, UserPreference, Memory
│   │   └── session.py                   # SQLAlchemy engine & session factory (Neon DB)
│   ├── orchestrator/                    # LangGraph orchestration state machine
│   │   ├── comparison_helper.py         # Spec extraction, product selection, comparison tables
│   │   ├── graph.py                     # StateGraph compilation & run_pipeline()
│   │   ├── nodes.py                     # Agent wrappers & routing logic
│   │   └── state.py                     # Shared pipeline state schema
│   ├── Agents/                          # Seven specialized AI agents
│   │   ├── query_understanding/         # Category & constraint extraction
│   │   ├── retrieval/                   # ChromaDB semantic search
│   │   ├── memory/                      # Dynamic persona & preference management
│   │   ├── ranking/                     # Multi-signal scoring
│   │   ├── xai/                         # Explainable recommendation reasoning
│   │   ├── follow_up/                   # Contextual follow-up actions
│   │   ├── response/                    # Final response synthesis & image binding
│   │   └── gemini_retry.py              # Robust API retry handler
│   └── pipeline/
│       ├── product_images.py            # High-performance Parquet image lookup
│       ├── retrieval.py                 # ProductRetriever class (optimized title search)
│       └── sentiment_analysis.py        # Review sentiment processing
├── frontend/
│   ├── index.html                       # HTML entry point with SmartPick favicon & typography
│   ├── package.json                     # Vite & test scripts
│   ├── src/
│   │   ├── App.jsx                      # ChatGPT-style full-viewport app layout
│   │   ├── App.css                      # Warm editorial design system tokens
│   │   ├── api/recommend.js             # FastAPI recommendation & auth client
│   │   ├── constants/
│   │   │   └── categories.js            # 7 categories & dynamic example queries
│   │   ├── context/
│   │   │   └── AuthContext.jsx          # User login state & JWT token provider
│   │   ├── components/
│   │   │   ├── CategoryBar.jsx          # 7-category interactive navigation pills
│   │   │   ├── ChatInput.jsx            # Multi-category anchored search composer
│   │   │   ├── ChatWindow.jsx           # Clean conversation thread with start-anchored scroll
│   │   │   ├── MessageBubble.jsx        # Recommendation overview, cards & comparison table
│   │   │   ├── MessageBubble.css        # Responsive comparison cards & table styles
│   │   │   ├── ProductCard.jsx          # Circular rank badge (#1–#5), photo, price & tags
│   │   │   ├── ProfileSelector.jsx      # Persona dropdown & account auth modal trigger
│   │   │   ├── FollowUpChips.jsx        # Clickable follow-up prompt pills
│   │   │   └── auth/                    # Modal, Login, Signup, OTP, Password Reset
│   │   └── __tests__/
│   │       └── ux_category_and_comparison.test.mjs  # Frontend Node 22 test suite
├── data/
│   ├── chromadb/                        # ChromaDB vector index (250,000+ products)
│   └── products_master.parquet          # Master catalog with authentic image URLs
├── tests/
│   ├── test_all_categories.py           # Multi-category LangGraph pipeline evaluation
│   ├── test_auth.py                     # Auth endpoints, JWT, & password hashing
│   ├── test_auth_brevo_workflow.py      # Brevo OTP email delivery & retry flows
│   ├── test_category_eval_fixes.py      # Category evaluation & constraint tests
│   ├── test_database.py                 # Neon DB models & relationships
│   ├── test_e2e_frontend_auth_and_recommendation.py  # End-to-end signup-to-recommendation flow
│   ├── test_fastapi_endpoints.py        # Live FastAPI endpoints & CORS tests
│   ├── test_gemini_reliability.py       # Quota retry & fallback tests
│   ├── test_langgraph_pipeline.py       # Pipeline routing & guard tests
│   ├── test_memory_and_isolation.py     # Multi-user & anonymous isolation tests
│   ├── test_product_images.py           # Image URL resolution & fallback tests
│   ├── test_retrieval_regression.py     # Retrieval exclusions & spec extraction
│   └── test_ux_and_comparison_regression.py # Category context & comparison table tests
└── requirements.txt                     # Python backend dependencies
```

---

## Setup & Installation

### Prerequisites

* **Python 3.10+**
* **Node.js 18+** & **npm**
* **Google Gemini API Key**
* **Neon PostgreSQL Database**
* **Brevo API Key** (for transactional OTP email verification)

### 1. Clone & Set Up Python Environment

```bash
git clone <repo-url>
cd SmartPick

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
# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# Neon PostgreSQL Database
DATABASE_URL=postgresql://user:password@ep-example.neon.tech/smartpick?sslmode=require

# Authentication & JWT
JWT_SECRET_KEY=your_32_byte_jwt_secret_key_here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Brevo Transactional Email Service
BREVO_API_KEY=your_brevo_api_key_here
BREVO_SENDER_EMAIL=noreply@smartpick.ai
BREVO_SENDER_NAME=SmartPick
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
# From project root with .venv activated
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

### Recommendation & Core Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Root status endpoint (`{"message": "SmartPick backend is running"}`) |
| `/health` | `GET` | Health check with supported categories count (`6`) |
| `/understand` | `POST` | Inspect Query Understanding agent output for debugging |
| `/recommend` | `POST` | Primary recommendation endpoint with optional category context |

### Authentication Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/auth/signup` | `POST` | Register a new user and dispatch 6-digit OTP email |
| `/auth/verify-email` | `POST` | Verify registration OTP challenge and issue JWT token |
| `/auth/login` | `POST` | Authenticate with username/email and password |
| `/auth/me` | `GET` | Retrieve authenticated user profile and preference state |
| `/auth/resend-otp` | `POST` | Resend verification OTP with 60-second cooldown protection |
| `/auth/forgot-password`| `POST` | Request password reset challenge code |
| `/auth/reset-password` | `POST` | Set new password using verified challenge code |

### Example Request: Product Recommendation with Category Context

```bash
curl -X POST http://127.0.0.1:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Samsung phone under ₹30000 with 8GB RAM",
    "category": "Cell Phones & Accessories",
    "user_id": "budget_conscious",
    "top_k": 5
  }'
```

### Example Request: Side-by-Side Product Comparison

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

### Example Structured Response (with Side-by-Side Comparison)

```json
{
  "summary": "Here is a side-by-side comparison of Galaxy S10 5G and Galaxy A51.",
  "recommendations": [
    {
      "asin": "B07RPHM14M",
      "title": "Galaxy S10 5G 8GB RAM 256GB",
      "brand": "SAMSUNG",
      "price_inr": 28687.0,
      "image_url": "https://m.media-amazon.com/images/I/41lVosxv3pL._AC_.jpg",
      "explanation": "Flagship device with premium display and larger storage.",
      "key_factors": ["8GB RAM", "256GB Storage", "Under ₹30,000"]
    },
    {
      "asin": "B08N5WRWNW",
      "title": "Galaxy A51 8GB RAM 128GB",
      "brand": "SAMSUNG",
      "price_inr": 22499.0,
      "image_url": "https://m.media-amazon.com/images/I/41aXYZ123L._AC_.jpg",
      "explanation": "Cost-effective mid-range alternative with solid battery life.",
      "key_factors": ["8GB RAM", "128GB Storage", "Lower Price"]
    }
  ],
  "comparison": {
    "heading": "Comparing SAMSUNG vs SAMSUNG",
    "product_a_asin": "B07RPHM14M",
    "product_b_asin": "B08N5WRWNW",
    "rows": [
      { "aspect": "Price", "product_a": "₹28,687", "product_b": "₹22,499" },
      { "aspect": "RAM", "product_a": "8GB", "product_b": "8GB" },
      { "aspect": "Storage", "product_a": "256GB", "product_b": "128GB" },
      { "aspect": "Battery", "product_a": "4500 mAh", "product_b": "4000 mAh" }
    ],
    "conclusion": "The Galaxy S10 5G provides double the onboard storage (256GB) and larger battery capacity for a modest ₹6,188 price premium, making it ideal for power users. The Galaxy A51 is better suited if staying well under ₹25,000 is your top priority."
  },
  "additional_information": "Both phones feature 8GB RAM and are backed by authentic catalog data.",
  "follow_up_suggestions": [
    "Would you like to explore accessories for Galaxy S10?",
    "Check customer reviews on camera performance"
  ]
}
```

---

## Testing & Quality Verification

SmartPick includes comprehensive automated test suites for both backend and frontend.

### 1. Backend Test Suite (146 Tests)

```bash
# Run the complete pytest suite
.venv\Scripts\python.exe -m pytest tests
```

* **146 passed in ~18 seconds** (100% pass rate)
* Covers authentication, Brevo email verification workflows, database isolation, retrieval regression, category constraint rules, image fallback resolution, LangGraph routing, Gemini quota retry reliability, and product comparison tables.

### 2. Frontend Test Suite

```bash
cd frontend
npm test
```

* Uses Node.js 22 built-in test runner (`node --test`)
* Verifies all 7 category states, 6 canonical and 3 category-specific query counts, demo query removal, search isolation, and comparison data schemas.

### 3. Frontend Production Build

```bash
cd frontend
npm run build
```

* Compiles with TypeScript check and Vite production bundling (`0 errors`).

---

## User Personas (Personalization Demo)

SmartPick supports dynamic user preference profiles:

| Persona ID | Label | Behavioral Bias |
|---|---|---|
| `anonymous` | **Standard Search** | Neutral baseline (no personalization applied) |
| `budget_conscious` | **Budget Conscious** | Strong preference for maximum value and lower price tiers |
| `camera_focused` | **Quality & Optics** | Prioritizes build quality, premium optics, and top sentiment |
| `samsung_loyalist` | **Brand Loyalist** | Prioritizes preferred brand affinity |

When logged in via Neon PostgreSQL, user preferences adapt dynamically to previous searches and interactions with strict multi-user data isolation.

---

## License

This project is developed for educational, academic, and research purposes.
