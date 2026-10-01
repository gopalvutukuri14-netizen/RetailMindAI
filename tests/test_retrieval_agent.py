# backend/pipeline/test_retrieval_agent.py
from backend.Agents.query_understanding import QueryUnderstandingAgent
from backend.Agents.retrieval import RetrievalAgent


def main():
    print("Running Query Understanding...")
    qu_agent = QueryUnderstandingAgent()
    query = "Samsung phone under ₹15,000 with good camera and long battery"
    understood = qu_agent.understand(query)
    print(understood.model_dump_json(indent=2))

    print("\nRunning Retrieval...")
    retrieval_agent = RetrievalAgent()
    result = retrieval_agent.retrieve(understood, top_k=5)

    print(f"\nSemantic query used: {result.query_text_used}")
    print(f"Filters applied: {result.hard_filters_applied}")
    print(f"Constraints NOT enforced: {result.hard_constraints_not_enforced}")
    print(f"\n{'='*70}\nTOP {result.total_candidates_returned} RESULTS\n{'='*70}")

    for i, p in enumerate(result.products, start=1):
        print(f"\n{i}. {p.title}")
        print(f"   Brand: {p.brand} | Price: ₹{p.price_inr} | Distance: {p.distance:.4f}")
        print(f"   RAM: {p.ram_gb}GB (meets: {p.meets_ram}) | Battery: {p.battery_mah}mAh (meets: {p.meets_battery})")


if __name__ == "__main__":
    main()