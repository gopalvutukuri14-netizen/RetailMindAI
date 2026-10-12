"""
Full Seven-Agent LangGraph Pipeline Evaluation for RetailMind AI.

Runs the real end-to-end pipeline against ChromaDB and Gemini for all six product categories:
1. Phones: Samsung phone under ₹30000 with 8GB RAM
2. Electronics: Wireless headphones for gaming under ₹5000
3. Home & Kitchen: Non-stick cookware set under ₹10000
4. Clothing: Durable jacket under ₹5000
5. Office Products: Comfortable ergonomic office chair
6. Sports & Outdoors: Durable running shoes

Separates graph execution success from relevance validation checks.
Inspects real graph state to verify that all seven agents executed.
"""

import sys
import json
from dataclasses import dataclass, field
from typing import Any

from backend.orchestrator.graph import run_pipeline
from backend.Agents.response.schema import ResponseResult
from backend.Agents.query_understanding.schema import QueryUnderstanding
from backend.Agents.retrieval.schema import RetrievalResult
from backend.Agents.memory.schema import UserProfile
from backend.Agents.ranking.schema import RankingResult
from backend.Agents.xai.schema import XAIResult
from backend.Agents.follow_up.schema import FollowUpResult


@dataclass
class EvaluationReport:
    category: str
    query: str
    execution_pass: bool = False
    relevance_pass: bool = False
    agent_status: dict[str, str] = field(default_factory=dict)
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)


TEST_CASES = [
    {
        "category": "Phones",
        "query": "Samsung phone under ₹30000 with 8GB RAM",
        "user_id": "budget_conscious",
        "expected_category": "Cell_Phones_and_Accessories",
        "expected_product_type": "phone",
        "budget_max": 30000.0,
        "ram_required": 8.0,
    },
    {
        "category": "Electronics",
        "query": "Wireless headphones for gaming under ₹5000",
        "user_id": "gamer",
        "expected_category": "Electronics",
        "expected_product_type": "headphones",
        "budget_max": 5000.0,
        "wireless_required": True,
    },
    {
        "category": "Home & Kitchen",
        "query": "Non-stick cookware set under ₹10000",
        "user_id": "home_cook",
        "expected_category": "Home_and_Kitchen",
        "expected_product_type": "cookware set",
        "budget_max": 10000.0,
    },
    {
        "category": "Clothing",
        "query": "Durable jacket under ₹5000",
        "user_id": "outdoor_enthusiast",
        "expected_category": "Clothing_Shoes_and_Jewelry",
        "expected_product_type": "jacket",
        "budget_max": 5000.0,
    },
    {
        "category": "Office Products",
        "query": "Comfortable ergonomic office chair",
        "user_id": "wfh_professional",
        "expected_category": "Office_Products",
        "expected_product_type": "office chair",
        "budget_max": None,
    },
    {
        "category": "Sports & Outdoors",
        "query": "Durable running shoes",
        "user_id": "runner",
        "expected_category": "Sports_and_Outdoors",
        "expected_product_type": "running shoes",
        "budget_max": None,
    },
]


def verify_seven_agents(final_state: dict) -> dict[str, str]:
    """Verify execution of each agent by inspecting accumulated LangGraph state."""
    agents = {}

    # 1. Query Understanding Agent
    qu = final_state.get("query_understanding")
    if isinstance(qu, QueryUnderstanding):
        agents["1. Query Understanding Agent"] = f"EXECUTED (intent={qu.intent.value}, category={qu.category})"
    else:
        agents["1. Query Understanding Agent"] = "NOT EXECUTED"

    # 2. Retrieval Agent
    ret = final_state.get("retrieval_result")
    if isinstance(ret, RetrievalResult):
        agents["2. Retrieval Agent"] = f"EXECUTED ({ret.total_candidates_returned} candidates retrieved)"
    else:
        agents["2. Retrieval Agent"] = "NOT EXECUTED"

    # 3. Memory Agent
    mem = final_state.get("user_profile")
    if isinstance(mem, UserProfile):
        agents["3. Memory Agent"] = f"EXECUTED (user_id='{mem.user_id}', preferred={mem.preferred_brands})"
    else:
        agents["3. Memory Agent"] = "NOT EXECUTED"

    # 4. Ranking Agent
    rnk = final_state.get("ranking_result")
    if isinstance(rnk, RankingResult):
        agents["4. Ranking Agent"] = f"EXECUTED ({rnk.total_ranked} products scored & sorted)"
    else:
        agents["4. Ranking Agent"] = "NOT EXECUTED"

    # 5. XAI Agent
    xai = final_state.get("xai_result")
    if isinstance(xai, XAIResult):
        agents["5. XAI Agent"] = f"EXECUTED ({len(xai.explanations)} explanations generated)"
    else:
        agents["5. XAI Agent"] = "NOT EXECUTED"

    # 6. Follow-up Agent
    flw = final_state.get("followup_result")
    if isinstance(flw, FollowUpResult):
        agents["6. Follow-up Agent"] = f"EXECUTED ({len(flw.suggestions)} suggestions generated)"
    else:
        agents["6. Follow-up Agent"] = "NOT EXECUTED"

    # 7. Response Agent
    resp = final_state.get("response_result")
    if isinstance(resp, ResponseResult):
        agents["7. Response Agent"] = f"EXECUTED ({len(resp.recommendations)} final recommendations structured)"
    else:
        agents["7. Response Agent"] = "NOT EXECUTED"

    return agents


def evaluate_query(tc: dict) -> EvaluationReport:
    report = EvaluationReport(
        category=tc["category"],
        query=tc["query"],
    )

    print("\n" + "=" * 80)
    print(f"EVALUATING CATEGORY: {tc['category'].upper()}")
    print(f"QUERY: {tc['query']}")
    print(f"USER PROFILE ID: {tc['user_id']}")
    print("=" * 80)

    # 1. Run real pipeline with full state extraction
    try:
        response_result, final_state = run_pipeline(
            raw_query=tc["query"],
            user_id=tc["user_id"],
            top_k=5,
            return_state=True,
        )
        report.execution_pass = True
    except Exception as exc:
        report.execution_pass = False
        report.checks_failed.append(f"Pipeline crashed with unhandled exception: {exc}")
        print(f"CRITICAL ERROR: Pipeline execution failed: {exc}")
        return report

    # 2. Verify all seven agents ran
    agent_status = verify_seven_agents(final_state)
    report.agent_status = agent_status

    print("\n[AGENT EXECUTION AUDIT (REAL GRAPH STATE)]")
    all_agents_executed = True
    for agent_name, status in agent_status.items():
        is_ok = "EXECUTED" in status
        symbol = "[OK]" if is_ok else "[FAIL]"
        print(f"  {symbol} {agent_name}: {status}")
        if not is_ok:
            all_agents_executed = False

    if all_agents_executed:
        report.checks_passed.append("All 7 agents executed and recorded output in pipeline state.")
    else:
        report.checks_failed.append("One or more agents failed to record output in pipeline state.")

    # 3. Parsed Query Understanding Audit
    qu = final_state.get("query_understanding")
    print("\n[PARSED QUERY UNDERSTANDING]")
    if qu:
        print(f"  - Intent         : {qu.intent.value}")
        print(f"  - Category       : {qu.category}")
        print(f"  - Product Type   : {qu.product_type}")
        print(f"  - Budget         : ₹{qu.budget_min} to ₹{qu.budget_max}")
        print(f"  - Preferred Brand: {qu.brand.preferred}")
        print(f"  - Excluded Brand : {qu.brand.excluded}")
        print(f"  - Specs          : RAM={qu.specs.ram_gb}GB, Storage={qu.specs.storage_gb}GB, Camera={qu.specs.camera_mp_min}MP")
        print(f"  - Quality Tags   : {qu.quality_tags}")
        print(f"  - Hard Bounds    : {qu.hard_constraints}")

        if tc.get("expected_category") and getattr(qu.category, "value", str(qu.category)) == tc["expected_category"]:
            report.checks_passed.append(f"Category correctly parsed as '{tc['expected_category']}'.")
        elif tc.get("expected_category"):
            report.checks_failed.append(f"Category parsed as '{qu.category}', expected '{tc['expected_category']}'.")

        if tc.get("expected_product_type") and qu.product_type == tc["expected_product_type"]:
            report.checks_passed.append(f"Product type correctly identified as '{tc['expected_product_type']}'.")

        if tc.get("budget_max") is not None:
            if qu.budget_max == tc["budget_max"]:
                report.checks_passed.append(f"Budget cap parsed accurately as ₹{tc['budget_max']}.")
            else:
                report.checks_failed.append(f"Budget cap parsed as {qu.budget_max}, expected {tc['budget_max']}.")
    else:
        report.checks_failed.append("Query Understanding object missing.")

    # 4. Retrieval & Ranking Counts
    ret = final_state.get("retrieval_result")
    rnk = final_state.get("ranking_result")
    ret_count = ret.total_candidates_returned if ret else 0
    rnk_count = rnk.total_ranked if rnk else 0
    rec_count = len(response_result.recommendations)

    print("\n[CANDIDATE COUNTS]")
    print(f"  - Retrieved from ChromaDB : {ret_count}")
    print(f"  - Scored & Ranked by Agent : {rnk_count}")
    print(f"  - Final Recommendations   : {rec_count}")

    if rec_count > 0:
        report.checks_passed.append(f"Pipeline returned {rec_count} recommendations.")
    else:
        report.checks_failed.append("Pipeline returned 0 recommendations.")

    # 5. Final Recommendations & Domain Relevance Checks
    print("\n[FINAL RECOMMENDATIONS]")
    recommendations = response_result.recommendations
    category_name = tc["category"]

    relevance_ok = True

    for i, prod in enumerate(recommendations, 1):
        title_lower = prod.title.casefold()
        print(f"\n  {i}. {prod.title}")
        print(f"     Brand: {prod.brand or 'N/A'} | Price: {f'₹{prod.price_inr}' if prod.price_inr is not None else 'None (unspecified)'}")
        print(f"     Explanation: {prod.explanation}")
        print(f"     Key Factors: {prod.key_factors}")

        # Check: Missing prices must remain None
        if prod.price_inr is None:
            # Check JSON serialization produces null
            json_dump = prod.model_dump_json()
            if '"price_inr":null' in json_dump.replace(" ", ""):
                report.checks_passed.append(f"Product #{i} missing price correctly serialized to null.")
            else:
                relevance_ok = False
                report.checks_failed.append(f"Product #{i} missing price failed JSON null check: {json_dump}")

        # Check: Budget constraint (if price is known)
        if tc.get("budget_max") is not None and prod.price_inr is not None:
            if prod.price_inr > tc["budget_max"] * 1.05:  # 5% tolerance max
                relevance_ok = False
                report.checks_failed.append(f"Product #{i} price ₹{prod.price_inr} exceeds budget ₹{tc['budget_max']}.")

        # Domain Specific Relevance Checks:
        if category_name == "Phones":
            # 1. 8GB RAM requirement: Incompatible RAM must NOT be present
            # Look up candidate metadata in ret
            ret_prod = next((p for p in (ret.products if ret else []) if p.asin == prod.asin), None)
            ram = ret_prod.ram_gb if ret_prod else None
            meets_ram = ret_prod.meets_ram if ret_prod else None

            if ram is not None and ram < 8.0:
                relevance_ok = False
                report.checks_failed.append(f"FAIL: Product #{i} has {ram}GB RAM (< 8GB required): '{prod.title}'")
            elif ram is not None and ram >= 8.0:
                report.checks_passed.append(f"Product #{i} verified with {ram}GB RAM.")
            elif ram is None:
                # Unknown RAM must NOT be falsely claimed as verified 8GB
                if "verified 8gb" in prod.explanation.lower() or "8gb ram verified" in prod.explanation.lower():
                    relevance_ok = False
                    report.checks_failed.append(f"FAIL: Product #{i} has unknown RAM but explanation claims verified 8GB.")
                else:
                    report.checks_passed.append(f"Product #{i} has unspecified RAM and is kept without false claims.")

        elif category_name == "Electronics":
            # 2. Wireless Headphones: Must not be books/pictorials or wired-only
            if any(term in title_lower for term in ("isbn", "pictorial", "book", "guide")):
                relevance_ok = False
                report.checks_failed.append(f"FAIL: Product #{i} is a book/pictorial, not headphones: '{prod.title}'")

            is_wired = "wired" in title_lower and not ("wireless" in title_lower or "bluetooth" in title_lower)
            if is_wired:
                relevance_ok = False
                report.checks_failed.append(f"FAIL: Product #{i} is wired-only for wireless query: '{prod.title}'")

        elif category_name == "Home & Kitchen":
            # 3. Cookware set: Must not be wooden spoons or utensil sets
            is_utensil = any(term in title_lower for term in (
                "wooden spoon", "wooden spoons", "wooden utensils",
                "cooking utensils", "utensil set", "spatula set",
            ))
            if is_utensil and not any(cw in title_lower for cw in ("pot", "pan", "cookware set")):
                relevance_ok = False
                report.checks_failed.append(f"FAIL: Product #{i} is a utensil/spoon set, not cookware: '{prod.title}'")

        elif category_name == "Clothing":
            # 4. Jackets: Must be jackets/outerwear
            is_jacket = any(term in title_lower for term in ("jacket", "coat", "parka", "windbreaker", "vest", "outwear", "outerwear"))
            if not is_jacket:
                relevance_ok = False
                report.checks_failed.append(f"Product #{i} may not be a jacket: '{prod.title}'")

        elif category_name == "Office Products":
            # 5. Office chair: Must be chair
            is_chair = any(term in title_lower for term in ("chair", "seating"))
            if not is_chair:
                relevance_ok = False
                report.checks_failed.append(f"Product #{i} may not be an office chair: '{prod.title}'")

        elif category_name == "Sports & Outdoors":
            # 6. Running shoes: Must not be sparring or combat shoes
            is_combat = any(term in title_lower for term in ("sparring", "boxing", "wrestling", "cleats", "martial arts"))
            if is_combat:
                relevance_ok = False
                report.checks_failed.append(f"FAIL: Product #{i} is combat/sparring footwear, not running shoes: '{prod.title}'")

    # 6. XAI Explanations & Follow-up questions audit
    print("\n[XAI & FOLLOW-UP SUGGESTIONS]")
    print(f"  Summary: {response_result.summary}")
    print(f"  Follow-up Suggestions ({len(response_result.follow_up_suggestions)}):")
    for s in response_result.follow_up_suggestions:
        print(f"    * {s}")

    if response_result.summary and len(response_result.summary.strip()) > 10:
        report.checks_passed.append("Response summary is descriptive and grounded.")
    else:
        report.checks_failed.append("Response summary is missing or too short.")

    if len(response_result.follow_up_suggestions) >= 1:
        report.checks_passed.append(f"{len(response_result.follow_up_suggestions)} follow-up suggestions provided.")
    else:
        report.checks_failed.append("Zero follow-up suggestions provided.")

    # 7. Overall relevance assessment
    report.relevance_pass = relevance_ok and (rec_count > 0)
    return report


def run_full_evaluation():
    print("\n" + "#" * 80)
    print("RETAILMIND AI — FULL SEVEN-AGENT PIPELINE EVALUATION")
    print("Testing real LangGraph workflow across all six product categories")
    print("#" * 80)

    reports: list[EvaluationReport] = []

    for tc in TEST_CASES:
        report = evaluate_query(tc)
        reports.append(report)

    # ── Final Summary Table ───────────────────────────────────────
    print("\n\n" + "=" * 80)
    print("FINAL EVALUATION SUMMARY REPORT")
    print("=" * 80)
    header = f"{'Category':<22} | {'Graph Exec':<10} | {'Relevance':<10} | {'Agents (7/7)':<12} | {'Checks (Pass/Fail)'}"
    print(header)
    print("-" * 80)

    total_exec_pass = 0
    total_rel_pass = 0

    for rep in reports:
        exec_str = "PASS" if rep.execution_pass else "FAIL"
        rel_str = "PASS" if rep.relevance_pass else "FAIL"
        agents_count = sum(1 for v in rep.agent_status.values() if "EXECUTED" in v)
        agents_str = f"{agents_count}/7"

        checks_str = f"{len(rep.checks_passed)} pass, {len(rep.checks_failed)} fail"

        if rep.execution_pass:
            total_exec_pass += 1
        if rep.relevance_pass:
            total_rel_pass += 1

        print(f"{rep.category:<22} | {exec_str:<10} | {rel_str:<10} | {agents_str:<12} | {checks_str}")

    print("-" * 80)
    print(f"TOTAL EXECUTION PASS: {total_exec_pass}/{len(reports)}")
    print(f"TOTAL RELEVANCE PASS: {total_rel_pass}/{len(reports)}")
    print("=" * 80)

    # Print failures if any
    all_failures = []
    for rep in reports:
        for f in rep.checks_failed:
            all_failures.append(f"[{rep.category}] {f}")

    if all_failures:
        print("\nIDENTIFIED ISSUES / DEFECTS:")
        for fail in all_failures:
            print(f"  * {fail}")
        print()
    else:
        print("\nALL RELEVANCE AND EXECUTION CRITERIA MET WITH ZERO DEFECTS!\n")

    return reports


if __name__ == "__main__":
    run_full_evaluation()
