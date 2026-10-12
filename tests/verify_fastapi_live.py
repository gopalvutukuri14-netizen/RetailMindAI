"""
Live FastAPI Endpoints Verification Script for RetailMind AI.

Executes real HTTP requests via TestClient(app) without mocks:
1. GET /
2. GET /health
3. POST /understand
4. POST /recommend (general intent: "bye")
5. POST /recommend (product recommendation: full 7-agent pipeline)
"""

import sys
import json

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from fastapi.testclient import TestClient

from backend.main import app


def run_live_verification():
    print("=" * 70)
    print("RetailMind AI - Live FastAPI Endpoint Smoke Verification")
    print("=" * 70)

    client = TestClient(app)

    # 1. GET /
    print("\n[1] Testing GET / ...")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.json() == {"message": "SmartPick backend is running"}

    # 2. GET /health
    print("\n[2] Testing GET /health ...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print(f"Status: {res.status_code}")
    print(f"Response: {res.json()}")
    assert res.json() == {"status": "healthy"}

    # 3. POST /understand
    print("\n[3] Testing POST /understand with live QueryUnderstandingAgent ...")
    query_payload = {"query": "Samsung phone under 30000 with 8GB RAM"}
    res = client.post("/understand", json=query_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    qu_data = res.json()
    print(f"Status: {res.status_code}")
    print(f"Parsed Intent: {qu_data.get('intent')}")
    print(f"Parsed Category: {qu_data.get('category')}")
    print(f"Parsed Product Type: {qu_data.get('product_type')}")
    print(f"Parsed Price Max: {qu_data.get('price_max_inr')}")
    assert qu_data.get("intent") in ["product_recommendation", "product_pipeline"]
    assert qu_data.get("category") == "Cell_Phones_and_Accessories"

    # 4. POST /recommend (General Intent: "bye")
    print("\n[4] Testing POST /recommend (general intent: 'bye') ...")
    res = client.post("/recommend", json={"query": "bye"})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    gen_data = res.json()
    print(f"Status: {res.status_code}")
    print(f"Summary: {gen_data.get('summary')}")
    print(f"Recommendations count: {len(gen_data.get('recommendations', []))}")
    assert len(gen_data.get("recommendations", [])) == 0
    assert len(gen_data.get("summary", "")) > 0

    # 5. POST /recommend (Live 7-agent product recommendation)
    print("\n[5] Testing POST /recommend with live 7-agent pipeline ...")
    rec_payload = {
        "query": "Samsung phone under ₹30000 with 8GB RAM",
        "user_id": "budget_conscious",
        "top_k": 3,
    }
    res = client.post("/recommend", json=rec_payload)
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    rec_data = res.json()
    print(f"Status: {res.status_code}")
    print(f"Summary: {rec_data.get('summary')[:100]}...")
    recs = rec_data.get("recommendations", [])
    print(f"Recommendations count: {len(recs)}")
    assert len(recs) > 0, "Expected at least 1 recommendation"

    for i, p in enumerate(recs, 1):
        print(f"\n  Product #{i}:")
        print(f"    ASIN: {p.get('asin')}")
        print(f"    Title: {p.get('title')[:60]}...")
        print(f"    Brand: {p.get('brand')}")
        print(f"    Price INR: {p.get('price_inr')}")
        print(f"    Image URL: {p.get('image_url')}")
        print(f"    Explanation: {p.get('explanation')[:80]}...")
        print(f"    Key Factors: {p.get('key_factors')}")
        # Validate schema constraints
        assert p.get("asin"), "Missing ASIN"
        assert p.get("title"), "Missing title"
        assert p.get("explanation"), "Missing explanation"
        assert isinstance(p.get("key_factors"), list), "key_factors must be a list"
        # Verify image_url is exposed (valid URL or None)
        assert p.get("image_url") is None or (isinstance(p.get("image_url"), str) and p.get("image_url").startswith("http")), "Invalid image_url format"
        # Verify missing price handling
        if p.get("price_inr") is not None:
            assert isinstance(p.get("price_inr"), (int, float)), "Price must be numeric if present"

    follow_ups = rec_data.get("follow_up_suggestions", [])
    print(f"\nFollow-up Suggestions ({len(follow_ups)}):")
    for s in follow_ups:
        print(f"  - {s}")
    assert isinstance(follow_ups, list)

    print("\n" + "=" * 70)
    print("All live FastAPI endpoint tests PASSED successfully!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        run_live_verification()
    except Exception as exc:
        print(f"\nFAILED: {exc}", file=sys.stderr)
        sys.exit(1)
