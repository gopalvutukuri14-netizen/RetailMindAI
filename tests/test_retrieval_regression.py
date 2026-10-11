"""
Regression tests for Stage B: Retrieval agent exclusions and specification extraction.

Verifies:
- B1: Phone exclusions filter out accessories (replacement battery, chargers, cases, etc.)
- B2: Headphone exclusions filter out adapters, cables, stands, guides, etc.
- B3: Cookware set exclusions filter out utensil sets, wooden spoons, spatulas, organizers, etc.
- B4: RAM extraction supports compact notation NGB+MGB (e.g. 8GB+256GB -> 8GB RAM).
- B5: Storage extraction supports compact notation NGB+MGB (e.g. 128GB+4GB -> 128GB storage).
"""

import pytest
from backend.Agents.retrieval.agent import RetrievalAgent


class TestProductTypeExclusions:
    """Test product-type exclusion and scoring rules."""

    @pytest.fixture
    def agent(self):
        # Instantiate RetrievalAgent with dummy retriever since we test scoring directly
        agent = object.__new__(RetrievalAgent)
        return agent

    @pytest.mark.parametrize(
        "title",
        [
            "Replacement Battery for Samsung Galaxy S20",
            "Fast Phone Charger USB-C 20W for iPhone and Samsung",
            "Wireless Charger Charging Pad for Smartphones",
            "Silicone Phone Case Protective Cover for Galaxy",
            "Tempered Glass Screen Protector for Smartphone",
            "Universal Car Mount Phone Holder",
            "Selfie Stick Tripod with Bluetooth Remote",
            "Replacement Battery for Phone 3000mAh",
            "USB Cable Phone Charger Cord Fast Charging",
        ],
    )
    def test_b1_phone_accessories_excluded(self, agent, title):
        """B1: Accessories must score <= 0 when product_type is phone."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="phone")
        assert score <= 0, f"Expected accessory '{title}' to be excluded, but got score {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Samsung Galaxy S23 5G 128GB Smartphone",
            "Google Pixel 8 Pro 256GB Unlocked Phone",
            "OnePlus 12R Smartphone with 5000mAh Battery",
            "Apple iPhone 15 128GB Blue",
            "Motorola Moto G 5G Cell Phone",
        ],
    )
    def test_b1_actual_phones_accepted(self, agent, title):
        """B1: Legitimate smartphones must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="phone")
        assert score > 0, f"Expected phone '{title}' to be accepted, but got score {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Audio Adapter 3.5mm Female to 6.35mm Male Jack",
            "Headphone Replacement Cable with Inline Mic",
            "Aluminum Headphone Stand Desk Headset Holder",
            "Replacement Ear Pads Cushions for Headphones",
            "Headphone Book: The Ultimate Audio Engineering Guide",
        ],
    )
    def test_b2_headphone_accessories_excluded(self, agent, title):
        """B2: Headphone accessories/adapters/books must score <= 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="headphones")
        assert score <= 0, f"Expected '{title}' to be excluded for headphones, but got score {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
            "Bose QuietComfort 45 Bluetooth Wireless Headphones",
            "Sennheiser HD 560 S Over-Ear Headphones",
        ],
    )
    def test_b2_actual_headphones_accepted(self, agent, title):
        """B2: Legitimate headphones must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="headphones")
        assert score > 0, f"Expected headphones '{title}' to be accepted, but got score {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "Silicone Cooking Utensil Set 12 Pcs Kitchen Spatula Set",
            "Natural Wooden Spoon Set for Cooking and Serving",
            "Stainless Steel Kitchen Utensils Spatula Set",
            "Pot Lid Organizer Rack Holder for Kitchen Cabinet",
            "Cotton Cooking Apron and Oven Mitt Set",
        ],
    )
    def test_b3_cookware_accessories_excluded(self, agent, title):
        """B3: Utensil sets, spatulas, wooden spoons, lid racks must score <= 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="cookware set")
        assert score <= 0, f"Expected '{title}' to be excluded for cookware set, but got score {score}"

    @pytest.mark.parametrize(
        "title",
        [
            "T-fal 12-Piece Nonstick Cookware Set Pots and Pans",
            "Cuisinart Stainless Steel 10-Piece Cookware Set",
            "Carote Nonstick Granite Cookware Set Induction Pots and Pans",
        ],
    )
    def test_b3_actual_cookware_sets_accepted(self, agent, title):
        """B3: Legitimate cookware sets must score > 0."""
        item = {"metadata": {"title": title}, "document": title}
        score = agent._product_type_score(item, product_type="cookware set")
        assert score > 0, f"Expected cookware set '{title}' to be accepted, but got score {score}"


class TestSpecExtraction:
    """Test specification extraction (RAM, storage, compact notation)."""

    def test_b4_and_b5_compact_ram_and_storage(self):
        """B4 & B5: '8GB+256GB' extracts 8GB RAM and 256GB Storage."""
        title = "Smartphone 8GB+256GB 5G Unlocked Dual SIM"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] == 8.0
        assert specs["storage_gb"] == 256.0

    def test_b4_and_b5_compact_reverse_order(self):
        """B4 & B5: '128GB+4GB' extracts 4GB RAM and 128GB Storage (smaller=RAM)."""
        title = "Budget Android Phone 128GB+4GB Green"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] == 4.0
        assert specs["storage_gb"] == 128.0

    def test_labelled_ram_and_storage(self):
        """Labelled notation takes standard precedence."""
        title = "Phone with 8GB RAM and 256GB Storage"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] == 8.0
        assert specs["storage_gb"] == 256.0

    def test_storage_tb_unit(self):
        """1TB Storage converts to 1024 GB."""
        title = "Flagship Phone 16GB RAM 1TB Storage"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] == 16.0
        assert specs["storage_gb"] == 1024.0

    def test_camera_and_battery_extraction(self):
        """Camera MP and battery mAh are correctly extracted."""
        title = "Smartphone 50MP Camera 5000mAh Battery"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["camera_mp"] == 50.0
        assert specs["battery_mah"] == 5000.0

    def test_missing_specs_return_none(self):
        """No specs mentioned leaves fields as None."""
        title = "Simple Case without specifications"
        specs = RetrievalAgent._extract_specifications(title)
        assert specs["ram_gb"] is None
        assert specs["storage_gb"] is None
        assert specs["camera_mp"] is None
        assert specs["battery_mah"] is None
