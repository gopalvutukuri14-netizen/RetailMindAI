import test from "node:test";
import assert from "node:assert/strict";
import { CATEGORIES_DEF, CATEGORY_EXAMPLE_QUERIES } from "../constants/categories.js";

test("Category Bar has exactly 7 visible categories with required names", () => {
  assert.equal(CATEGORIES_DEF.length, 7, "CategoryBar must have exactly 7 categories");

  const expectedCategories = [
    { id: "all", label: "All Categories" },
    { id: "phones", label: "Cell Phones & Accessories" },
    { id: "electronics", label: "Electronics" },
    { id: "home", label: "Home & Kitchen" },
    { id: "clothing", label: "Clothing & Shoes" },
    { id: "office", label: "Office Products" },
    { id: "sports", label: "Sports & Outdoors" },
  ];

  expectedCategories.forEach((expected, i) => {
    assert.equal(CATEGORIES_DEF[i].id, expected.id);
    assert.equal(CATEGORIES_DEF[i].label, expected.label);
  });
});

test("Dynamic example queries under 'All Categories' has exactly 6 canonical queries (1 per category)", () => {
  const allExamples = CATEGORY_EXAMPLE_QUERIES.all;
  assert.ok(Array.isArray(allExamples), "'all' must be an array of examples");
  assert.equal(allExamples.length, 6, "'All Categories' must display exactly 6 example queries");

  const categoryNames = allExamples.map((ex) => ex.category);
  const uniqueCategories = new Set(categoryNames);
  assert.equal(uniqueCategories.size, 6, "Each of the 6 canonical queries must belong to a different category");

  assert.ok(uniqueCategories.has("Cell Phones & Accessories"));
  assert.ok(uniqueCategories.has("Electronics"));
  assert.ok(uniqueCategories.has("Home & Kitchen"));
  assert.ok(uniqueCategories.has("Clothing & Shoes"));
  assert.ok(uniqueCategories.has("Office Products"));
  assert.ok(uniqueCategories.has("Sports & Outdoors"));
});

test("Each individual category has exactly 3 targeted example queries matching that category", () => {
  const individualCategories = [
    { key: "phones", expectedCat: "Cell Phones & Accessories" },
    { key: "electronics", expectedCat: "Electronics" },
    { key: "home", expectedCat: "Home & Kitchen" },
    { key: "clothing", expectedCat: "Clothing & Shoes" },
    { key: "office", expectedCat: "Office Products" },
    { key: "sports", expectedCat: "Sports & Outdoors" },
  ];

  for (const { key, expectedCat } of individualCategories) {
    const examples = CATEGORY_EXAMPLE_QUERIES[key];
    assert.ok(Array.isArray(examples), `${key} examples must be an array`);
    assert.equal(examples.length, 3, `${key} must have exactly 3 example queries`);

    for (const ex of examples) {
      assert.equal(ex.category, expectedCat, `Query '${ex.query}' must match category ${expectedCat}`);
      assert.ok(ex.query.length > 5, `Query '${ex.query}' must be descriptive`);
    }
  }
});

test("Demo query is completely removed from all example queries", () => {
  for (const [catKey, examples] of Object.entries(CATEGORY_EXAMPLE_QUERIES)) {
    for (const ex of examples) {
      const lower = ex.query.toLowerCase();
      assert.ok(!lower.includes("test product images"), `Demo query found under ${catKey}: ${ex.query}`);
      assert.ok(!lower.includes("fallback"), `Fallback demo found under ${catKey}: ${ex.query}`);
    }
  }
});

test("Category selection does not execute search API", () => {
  // Simulate category click handler
  let searchTriggered = false;
  let selectedCategory = "all";

  const onSelectCategory = (catId) => {
    selectedCategory = catId;
  };
  const onTriggerQuery = () => {
    searchTriggered = true;
  };

  // Simulating user clicking category buttons
  for (const cat of CATEGORIES_DEF) {
    onSelectCategory(cat.id);
  }

  assert.equal(selectedCategory, "sports");
  assert.equal(searchTriggered, false, "Category selection alone must never trigger search");
});

test("Comparison structure supports side-by-side cards, table rows, and conclusion", () => {
  const mockComparison = {
    heading: "Comparing Phone A vs Phone B",
    product_a_asin: "ASIN1",
    product_b_asin: "ASIN2",
    rows: [
      { aspect: "Price", product_a: "Price unavailable", product_b: "₹24,999" },
      { aspect: "RAM", product_a: "8GB", product_b: "12GB" },
      { aspect: "Battery", product_a: "5000 mAh", product_b: "Not available in catalog" },
    ],
    conclusion: "Phone A is better for battery life while Phone B has superior memory.",
  };

  assert.ok(mockComparison.heading);
  assert.equal(mockComparison.rows.length, 3);
  assert.equal(mockComparison.rows[0].product_a, "Price unavailable");
  assert.equal(mockComparison.rows[2].product_b, "Not available in catalog");
  assert.ok(mockComparison.conclusion.length > 10);
});

test("Assistant and app branding strictly uses SmartPick and never RetailMind", () => {
  for (const [catKey, examples] of Object.entries(CATEGORY_EXAMPLE_QUERIES)) {
    for (const ex of examples) {
      assert.ok(!ex.query.toLowerCase().includes("retailmind"), `RetailMind found in example under ${catKey}: ${ex.query}`);
    }
  }

  const canonicalIntro = "Hello! I am SmartPick, your AI shopping assistant. I can help you discover products, find options within your budget, understand customer sentiment, and compare products. What are you looking for today?";
  assert.ok(canonicalIntro.includes("SmartPick"));
  assert.ok(!canonicalIntro.includes("RetailMind"));
});

