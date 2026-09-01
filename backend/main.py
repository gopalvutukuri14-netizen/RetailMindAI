from fastapi import FastAPI
from pydantic import BaseModel

from backend.Agents.query_understanding import QueryUnderstandingAgent


app = FastAPI(title="RetailMind AI")


# Request body coming from the user
class QueryRequest(BaseModel):
    query: str


# Create the agent once when the server starts
agent = QueryUnderstandingAgent()


@app.get("/")
def root():
    return {"message": "RetailMind AI backend is running"}


@app.post("/understand")
def understand_query(request: QueryRequest):
    result = agent.understand(request.query)

    return result.model_dump()