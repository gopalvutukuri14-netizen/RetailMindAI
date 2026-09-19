from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.orchestrator import run_pipeline


app = FastAPI(
    title="RetailMind AI",
    description="AI-powered retail product recommendation system",
    version="1.0.0",
)

# Allow the React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ── Request / response models ───────────────────────────────────

class QueryRequest(BaseModel):
    query: str


class RecommendRequest(BaseModel):
    """Request body for the full recommendation pipeline."""
    query: str = Field(description="Natural-language shopping query")
    user_id: str = Field(
        default="anonymous",
        description="User profile ID for personalization (e.g. 'camera_focused', 'budget_conscious')",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of products to retrieve and rank",
    )


# ── Singleton agents ────────────────────────────────────────────

query_agent = QueryUnderstandingAgent()


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "RetailMind AI backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/understand")
def understand_query(request: QueryRequest):
    """Parse a user query into structured fields (debug endpoint)."""
    result = query_agent.understand(request.query)
    return result.model_dump()


@app.post("/recommend")
def recommend(request: RecommendRequest):
    """
    Full recommendation pipeline.

    Runs every agent in the correct order via the LangGraph
    orchestrator and returns the final structured response.
    """
    try:
        result = run_pipeline(
            raw_query=request.query,
            user_id=request.user_id,
            top_k=request.top_k,
        )
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))