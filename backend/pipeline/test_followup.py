# backend/pipeline/test_followup_agent.py
from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent
from backend.Agents.memory import MemoryAgent
from backend.Agents.ranking import RankingAgent
from backend.Agents.followup import FollowUpAgent


def main():
    qu = QueryUnderstandingAgent().understand(
        "Samsung phone under ₹15,000 with good camera and long battery"
    )
    retrieved = RetrievalAgent().retrieve(qu, top_k=5)
    profile = MemoryAgent().get_profile("samsung_loyalist")
    ranked = RankingAgent().rank(qu, retrieved, profile)
    followup_result = FollowUpAgent().suggest(qu, ranked)

    for s in followup_result.suggestions:
        print(f"[{s.suggestion_type.value}] {s.suggestion_text}")


if __name__ == "__main__":
    main()