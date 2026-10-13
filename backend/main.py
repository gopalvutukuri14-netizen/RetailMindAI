from typing import Optional
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.orchestrator import run_pipeline
from backend.auth import auth_router, get_current_user_optional
from backend.database.models import User

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SmartPick",
    description="AI-powered retail product recommendation system with explainable AI and authentication",
    version="1.1.0",
)

# Allow the React dev server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Authentication Router
app.include_router(auth_router)


# ?? Request / response models ???????????????????????????????????

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
    previous_products: list[dict] = Field(
        default_factory=list,
        description="Products from the last recommendation, for follow-up/comparison context",
    )


# ?? Endpoints ????????????????????????????????????????????????????

@app.get("/")
def root():
    return {"message": "SmartPick backend is running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/understand")
def understand_query(request: QueryRequest):
    """Parse a user query into structured fields (debug endpoint)."""
    # Initialize the agent lazily inside the request so that a missing
    # GEMINI_API_KEY causes a 500 response rather than a startup crash.
    from backend.Agents.query_understanding import QueryUnderstandingAgent
    try:
        agent = QueryUnderstandingAgent()
        result = agent.understand(request.query)
        return result.model_dump()
    except Exception as exc:
        logger.error("understand_query failed: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Query understanding failed. Please check the API key configuration.",
        )


@app.post("/recommend")
def recommend(
    request: RecommendRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Full recommendation pipeline.

    Runs every agent in the correct order via the LangGraph
    orchestrator and returns the final structured response.
    If authenticated via JWT, the verified user ID takes precedence over client body.
    """
    # Derive identity securely from authenticated token if logged in
    effective_user_id = current_user.id if current_user else request.user_id

    try:
        result = run_pipeline(
            raw_query=request.query,
            user_id=effective_user_id,
            top_k=request.top_k,
            previous_products=request.previous_products or None,
        )
        return result.model_dump()
    except Exception as exc:
        logger.error("recommend endpoint error: %s", exc, exc_info=True)
        # Sanitize: do not expose internal exception details to the client.
        raise HTTPException(
            status_code=500,
            detail=(
                "The recommendation pipeline encountered an error. "
                "This may be a temporary issue with the AI service."
            ),
        )
