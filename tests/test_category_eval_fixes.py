"""
Focused regression tests for observed defects and preservation requirements
from the live multi-category pipeline evaluation.

Verifies:
1. Phones: Queries requesting 8GB RAM strictly exclude products explicitly listing 4GB RAM (e.g. 128GB+4GB).
2. Wireless Gaming Headphones: Wired earbuds and books/pictorials are excluded; genuine wireless gaming headsets are accepted.
3. Cookware Sets: Wooden spoons and utensil sets are excluded; real pots and pans cookware sets are accepted.
4. Running Shoes: Sparring shoes (combat footwear) are excluded; genuine running shoes are accepted.
5. Preservation: Relevant jackets and ergonomic office chairs remain accepted with positive product-type scores.
6. Missing Prices: Missing prices remain None in Python models and serialize as null in JSON (never invented).
"""

import json
from unittest.mock import MagicMock
import pytest

from backend.Agents.retrieval.agent import RetrievalAgent
from backend.Agents.retrieval.schema import RetrievedProduct, RetrievalResult
from backend.Agents.ranking.agent import RankingAgent
from backend.Agents.ranking.schema import ScoreBreakdown
from backend.Agents.response.schema import ResponseProduct
from backend.Agents.query_understanding.schema import (
    QueryUnderstanding,
    Intent,
    RetailCategory,
    BrandPreferences,
    ProductSpecs,
)


# ===================================================================
# 1. PHONES: SPEC CONSTRAINTS & 128GB+4GB EXCLUSION
# ===================================================================

class TestPhonesSpecConstraints:
    """Verifies that queries with RAM requirements exclude products that explicitly fail."""

    @pytest.fixture
    def retrieval_agent(self):
        agent = object.__new__(RetrievalAgent)
        return agent

    @pytest.fixture
    def phone_query_8gb(self):
        return QueryUnderstanding(
            raw_query="Samsung phone under ₹30000 with 8GB RAM",
            intent=Intent.PRODUCT_RECOMMENDATION,
            category=RetailCategory.CELL_PHONES_AND_ACCESSORIES,
            product_type="phone",
            budget_max=30000.0,
            brand=BrandPreferences(preferred=["Samsung"]),
            specs=ProductSpecs(ram_gb=8.0),
        )

    def test_spec_extraction_4gb_ram_identified(self):
        """Title 'Black, 128GB+4GB' explicitly yields ram_gb=4.0."""
        title = (
            'Samsung Galaxy A22 4G LTE (NOT 5G) 6.4" HD+ Quad Camera 5000mAh Battery, '
            'Dual Sim GSM Unlocked Global 4G Volte (NOT VERIZON/Boost) International Model A255M (Black, 128GB+4GB)'
        )
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] == 4.0
        assert specs["storage_gb"] == 128.0

    def test_meets_ram_flag_is_false_for_4gb_when_8gb_requested(
        self, retrieval_agent, phone_query_8gb
    ):
        """A 4GB RAM phone must set meets_ram=False when 8GB RAM is requested."""
        item = {
            "asin": "B_A22",
            "distance": 0.4,
            "metadata": {
                "title": (
                    'Samsung Galaxy A22 4G LTE (NOT 5G) 6.4" HD+ Quad Camera 5000mAh Battery, '
                    'Dual Sim GSM Unlocked Global 4G Volte (NOT VERIZON/Boost) International Model A255M (Black, 128GB+4GB)'
                ),
                "brand": "Samsung",
                "price_inr": 11641.52,
            },
        }
        product = retrieval_agent._to_retrieved_product(item, phone_query_8gb)
        assert product.ram_gb == 4.0
        assert product.meets_ram is False

    def test_meets_ram_flag_is_true_for_8gb(
        self, retrieval_agent, phone_query_8gb
    ):
        """An 8GB RAM phone must set meets_ram=True when 8GB RAM is requested."""
        item = {
            "asin": "B_S10",
            "distance": 0.3,
            "metadata": {
                "title": "Galaxy S10 5G Enabled 6.7in SM-G977UZAVZW 8GB+256GB - Majestic Black",
                "brand": "Samsung",
                "price_inr": 28687.12,
            },
        }
        product = retrieval_agent._to_retrieved_product(item, phone_query_8gb)
        assert product.ram_gb == 8.0
        assert product.meets_ram is True

    def test_meets_ram_flag_is_none_when_unspecified(
        self, retrieval_agent, phone_query_8gb
    ):
        """A phone with unspecified RAM preserves meets_ram=None (not dropped)."""
        item = {
            "asin": "B_NOTE8",
            "distance": 0.35,
            "metadata": {
                "title": "Samsung Galaxy Note 8 N950U 64GB AT&T GSM Unlocked - Deep Sea Blue (Renewed)",
                "brand": "Samsung",
                "price_inr": 22703.12,
            },
        }
        product = retrieval_agent._to_retrieved_product(item, phone_query_8gb)
        assert product.ram_gb is None
        assert product.meets_ram is None

    def test_ranking_agent_disqualifies_explicit_spec_failures(self, phone_query_8gb):
        """RankingAgent must drop any product where meets_ram is False."""
        ranking_agent = RankingAgent()

        prod_4gb = RetrievedProduct(
            asin="B_FAIL",
            title="Samsung Galaxy A22 (Black, 128GB+4GB)",
            brand="Samsung",
            price_inr=11641.52,
            distance=0.2,  # Strong similarity
            ram_gb=4.0,
            meets_ram=False,  # Explicit failure!
        )
        prod_8gb = RetrievedProduct(
            asin="B_PASS",
            title="Galaxy S10 5G 8GB+256GB",
            brand="Samsung",
            price_inr=28687.12,
            distance=0.3,
            ram_gb=8.0,
            meets_ram=True,
        )
        prod_unknown = RetrievedProduct(
            asin="B_UNK",
            title="Samsung Galaxy Note 8 64GB",
            brand="Samsung",
            price_inr=22703.12,
            distance=0.35,
            ram_gb=None,
            meets_ram=None,
        )

        retrieval_res = RetrievalResult(
            query_text_used="Samsung phone",
            hard_filters_applied={},
            hard_constraints_not_enforced=[],
            total_candidates_returned=3,
            products=[prod_4gb, prod_8gb, prod_unknown],
        )

        ranked = ranking_agent.rank(phone_query_8gb, retrieval_res)
        ranked_asins = [p.asin for p in ranked.products]

        assert "B_FAIL" not in ranked_asins, "4GB phone must NOT be in ranked results when 8GB requested"
        assert "B_PASS" in ranked_asins
        assert "B_UNK" in ranked_asins


# ===================================================================
# 2. WIRELESS HEADPHONES: WIRED EARBUDS & BOOKS EXCLUSIONS
# ===================================================================

class TestWirelessGamingHeadphones:
    """Verifies that wired earbuds and books are excluded from wireless headphone queries."""

    @pytest.fixture
    def retrieval_agent(self):
        agent = object.__new__(RetrievalAgent)
        return agent

    def test_wired_earbuds_excluded_when_wireless_requested(self, retrieval_agent):
        """Wired earbuds must score <= 0 when query requests wireless headphones."""
        title = (
            "Earbuds Headphones with Microphone Pack of 5, Noise Isolating Wired Earbuds, "
            "Earphones with Powerful Heavy Bass Stereo, Compatible with Android, iPhone, iPad, "
            "Laptops, MP3 and Most 3.5mm Interface"
        )
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(
            item,
            product_type="headphones",
            quality_tags=["wireless", "gaming"],
            raw_query="Wireless headphones for gaming under ₹5000",
        )
        assert score <= 0, f"Expected wired earbuds to be excluded for wireless query, got {score}"

    def test_book_pictorial_excluded_from_headphones(self, retrieval_agent):
        """Books/pictorials with ISBN must score <= 0 for headphones queries."""
        title = "Headphone girl Pictorial ISBN: 4054042309 (2009) [Japanese Import]"
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(
            item,
            product_type="headphones",
            quality_tags=["wireless", "gaming"],
            raw_query="Wireless headphones for gaming under ₹5000",
        )
        assert score <= 0, f"Expected book/pictorial to be excluded, got {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "in-Ear Wireless TWS Earphones for Mobile Gaming, Bluetooth V5.2 Deep Bass 50ms Low Latency Headphones",
            "Headset Bluetooth Wireless Headset - HiFi Stereo Sound Quality, Bluetooth 5.1 Chip, Deep Noise Reduction",
            "Earbuds TWS Headphone tws4 BT 5.0 in-Ear Touch Control Wireless Earphones Earbuds",
        ],
    )
    def test_actual_wireless_gaming_headphones_accepted(self, retrieval_agent, title):
        """Legitimate wireless/bluetooth headphones must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(
            item,
            product_type="headphones",
            quality_tags=["wireless", "gaming"],
            raw_query="Wireless headphones for gaming under ₹5000",
        )
        assert score > 0, f"Expected legitimate wireless headset '{title}' to score > 0, got {score}"


# ===================================================================
# 3. COOKWARE SETS: WOODEN SPOONS & UTENSILS EXCLUSION
# ===================================================================

class TestCookwareSetExclusions:
    """Verifies that wooden spoons and utensil sets are excluded from cookware set queries."""

    @pytest.fixture
    def retrieval_agent(self):
        agent = object.__new__(RetrievalAgent)
        return agent

    def test_wooden_spoons_and_utensils_excluded(self, retrieval_agent):
        """Wooden spoons/utensil sets must score <= 0 for cookware set queries."""
        title = (
            "5 PCS Wooden Spoons for Cooking, Wooden Utensils for Cooking ，Durable Natural Teak "
            "Cooking Utensils, Wooden Spoons for Cooking - Non-Stick Natural Healthy Kitchen Cookware Set"
        )
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(item, product_type="cookware set")
        assert score <= 0, f"Expected wooden spoons/utensils to be excluded, got {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Pots and Pans Set, 7Pcs Ceramic Nonstick Cookware Set, Removable Handle, Suitable for Camping, RV, Induction",
            "Stackable Pots and Pans Set 10 Piece, Nonstick Cookware Set with Stackable Design Saves 55% More Space",
            "Fadware Induction Cookware Sets, Nonstick Pots and Pans Set 10 Piece, Dishwasher Safe Kitchen Cooking Pan",
            "T-fal 12-Piece Nonstick Cookware Set Pots and Pans",
        ],
    )
    def test_actual_cookware_sets_accepted(self, retrieval_agent, title):
        """Legitimate cookware sets (pots and pans) must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(item, product_type="cookware set")
        assert score > 0, f"Expected cookware set '{title}' to score > 0, got {score}"


# ===================================================================
# 4. RUNNING SHOES: SPARRING SHOES EXCLUSION
# ===================================================================

class TestRunningShoesExclusions:
    """Verifies that martial arts / sparring shoes are excluded from running shoe queries."""

    @pytest.fixture
    def retrieval_agent(self):
        agent = object.__new__(RetrievalAgent)
        return agent

    def test_sparring_shoes_excluded(self, retrieval_agent):
        """Ringstar FightPro Sparring Shoes must score <= 0 for running shoes query."""
        title = "Ringstar FightPro Sparring Shoes"
        item = {
            "metadata": {"title": title},
            "document": "Ringstar FightPro Sparring Shoes for martial arts combat training",
        }
        score = retrieval_agent._product_type_score(item, product_type="running shoes")
        assert score <= 0, f"Expected sparring shoes to be excluded for running shoes, got {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Salomon Sense Ride 4 Invisible GTX Men's Trail Running Shoes",
            "Salomon Men's Snowclog Trail Running Shoes Snow",
            "Slip On Running Shoes Men No Laces Fashion Summer and Autumn Men Sneakers",
            "Nike Air Zoom Pegasus 39 Running Shoes",
        ],
    )
    def test_actual_running_shoes_accepted(self, retrieval_agent, title):
        """Legitimate running shoes must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(item, product_type="running shoes")
        assert score > 0, f"Expected running shoe '{title}' to score > 0, got {score}"


# ===================================================================
# 5. PRESERVATION: JACKETS AND OFFICE CHAIRS
# ===================================================================

class TestPreservationRequirements:
    """Verifies that relevant jacket and office chair recommendations remain accepted."""

    @pytest.fixture
    def retrieval_agent(self):
        agent = object.__new__(RetrievalAgent)
        return agent

    @pytest.mark.parametrize(
        "title",
        [
            "DIOMOR Womens Fashion Lightweight Fullzip Hooded Rain Jacket Waterproof Raincoat Casual Windbreaker Outerwear",
            "Cherokee - Men's Outerwear Men's Twofer Quilted Vest Jacket",
            "IZOD Men's Water Resistant Midweight Jacket with Polar Fleece Lining",
            "JINSHI Winter Jackets for Men,Lightweight Puffer Jacket Windproof Warm Outwear for Travel Outdoor Hiking",
        ],
    )
    def test_jackets_remain_accepted(self, retrieval_agent, title):
        """Jacket recommendations must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(item, product_type="jacket")
        assert score > 0, f"Expected jacket '{title}' to score > 0, got {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Office Chair MORCOE High Back Ergonomic Executive Mesh Office Chair, Swivel Big and Tall Home Computer Chair",
            "Fuhe Office Chair Bonded Leather Chair Ergonomic Chair Executive Computer Desk Chair",
            "COMHOMA Office Chair Ergonomic Office Chair High Back Mesh Computer Chair with Lumbar Support",
        ],
    )
    def test_office_chairs_remain_accepted(self, retrieval_agent, title):
        """Office chair recommendations must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = retrieval_agent._product_type_score(item, product_type="office chair")
        assert score > 0, f"Expected office chair '{title}' to score > 0, got {score}"


# ===================================================================
# 6. MISSING PRICES: PRESERVED AS NONE AND SERIALIZED AS NULL
# ===================================================================

class TestMissingPricesPreservation:
    """Verifies that products without price preserve price_inr as None and serialize to null."""

    def test_retrieved_product_preserves_none_price(self):
        agent = object.__new__(RetrievalAgent)
        dummy_query = QueryUnderstanding(
            raw_query="chair",
            intent=Intent.PRODUCT_RECOMMENDATION,
            product_type="office chair",
        )
        item = {
            "asin": "B_CHAIR",
            "distance": 0.25,
            "metadata": {
                "title": "Office Chair MORCOE High Back Ergonomic Chair",
                "price_inr": None,  # Explicitly None / missing
            },
        }
        product = agent._to_retrieved_product(item, dummy_query)
        assert product.price_inr is None

    def test_response_product_preserves_none_price_and_serializes_to_null(self):
        resp_prod = ResponseProduct(
            asin="B_CHAIR",
            title="Office Chair MORCOE High Back Ergonomic Chair",
            brand="MORCOE",
            price_inr=None,
            explanation="Ergonomic support.",
        )
        assert resp_prod.price_inr is None

        serialized = resp_prod.model_dump()
        assert serialized["price_inr"] is None

        json_str = resp_prod.model_dump_json()
        parsed_json = json.loads(json_str)
        assert parsed_json["price_inr"] is None
        assert "null" in json_str
