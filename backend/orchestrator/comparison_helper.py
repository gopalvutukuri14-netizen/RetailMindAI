import re
from typing import Optional
from backend.Agents.response.schema import ComparisonRow, ComparisonData, ResponseProduct


def extract_product_specs(title_or_product: str | dict, category: Optional[str] = None) -> dict[str, str]:
    """
    Extract factual specs from product title/info based on category patterns.
    Returns empty dict if no clear specs are found.
    Never invents unstated specs.
    """
    if isinstance(title_or_product, dict):
        title = title_or_product.get("title") or ""
        desc = title_or_product.get("description") or ""
        full_text = f"{title} {desc}"
    else:
        full_text = str(title_or_product or "")

    specs = {}
    title_lower = full_text.casefold()

    # RAM (e.g. 8GB RAM, 8 GB RAM, 8GB)
    ram_match = re.search(r"(\d+)\s*(?:gb|mb)\s*ram", title_lower) or re.search(r"\b(\d+)\s*gb(?=\s*\+)", title_lower)
    if ram_match:
        specs["RAM"] = f"{ram_match.group(1).upper()}GB"

    # Storage (e.g. 128GB ROM, 256GB Storage, 128GB)
    storage_match = re.search(r"(\d+)\s*(?:gb|tb)\s*(?:storage|rom)", title_lower) or re.search(r"\+\s*(\d+)\s*gb", title_lower) or re.search(r"\b(64|128|256|512)\s*gb\b", title_lower)
    if storage_match:
        specs["Storage"] = f"{storage_match.group(1).upper()}GB"

    # Battery (e.g. 5000mah, 5000 mah)
    battery_match = re.search(r"(\d{3,5})\s*mah", title_lower)
    if battery_match:
        specs["Battery"] = f"{battery_match.group(1)} mAh"

    # Display (e.g. 6.7in, 6.7 inch, 6.7")
    display_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:in|inch|\")", title_lower)
    if display_match:
        specs["Display"] = f"{display_match.group(1)} inch"

    # Connectivity / Wireless
    if "5g" in title_lower:
        specs["Connectivity"] = "5G"
    elif "4g" in title_lower:
        specs["Connectivity"] = "4G LTE"
    elif "bluetooth" in title_lower or "wireless" in title_lower:
        specs["Connectivity"] = "Bluetooth / Wireless"

    # Noise cancellation
    if "anc" in title_lower or "active noise cancelling" in title_lower or "noise cancelling" in title_lower:
        specs["Noise Cancellation"] = "Active Noise Cancellation (ANC)"

    return specs


def select_two_products_to_compare(previous_products: list[dict], raw_query: str) -> tuple[dict, dict]:
    """
    Identify which two products from previous_products should be compared.
    Defaults to the top two products (index 0 and 1).
    """
    if len(previous_products) < 2:
        prod_a = previous_products[0] if previous_products else {}
        return prod_a, {}

    query_lower = raw_query.casefold()

    # Check for ordinal words like "first and third", "1st and 3rd"
    word_map = {
        "first": 0, "1st": 0,
        "second": 1, "2nd": 1,
        "third": 2, "3rd": 2,
        "fourth": 3, "4th": 3,
        "fifth": 4, "5th": 4,
    }
    found_ordinals = []
    for word, idx in word_map.items():
        if re.search(rf"\b{word}\b", query_lower):
            found_ordinals.append((query_lower.find(word), idx))

    if len(found_ordinals) >= 2:
        # Sort by position in string
        found_ordinals.sort(key=lambda x: x[0])
        idx_a, idx_b = found_ordinals[0][1], found_ordinals[1][1]
        if idx_a != idx_b and 0 <= idx_a < len(previous_products) and 0 <= idx_b < len(previous_products):
            return previous_products[idx_a], previous_products[idx_b]

    # Check for index mentions like "1 and 3" or "#1 and #3"
    index_matches = re.findall(r"(?:#|\bproduct\s*)?([1-9])\b", query_lower)
    if len(index_matches) >= 2:
        try:
            idx_a = int(index_matches[0]) - 1
            idx_b = int(index_matches[1]) - 1
            if 0 <= idx_a < len(previous_products) and 0 <= idx_b < len(previous_products) and idx_a != idx_b:
                return previous_products[idx_a], previous_products[idx_b]
        except (ValueError, IndexError):
            pass

    # Check for title / brand mentions
    matched_indices = []
    for idx, prod in enumerate(previous_products):
        brand = (prod.get("brand") or "").casefold().strip()
        title = (prod.get("title") or "").casefold().strip()
        if brand and brand in query_lower:
            matched_indices.append(idx)
        elif any(word in query_lower for word in title.split() if len(word) > 4):
            matched_indices.append(idx)

    matched_indices = list(dict.fromkeys(matched_indices))
    if len(matched_indices) >= 2:
        return previous_products[matched_indices[0]], previous_products[matched_indices[1]]

    # Default to top two
    return previous_products[0], previous_products[1]


def build_category_comparison_data(
    product_a: dict,
    product_b: dict,
    category: Optional[str] = None,
    gemini_comparison: Optional[ComparisonData] = None,
) -> ComparisonData:
    """
    Construct a complete, category-adapted ComparisonData instance.
    If gemini_comparison is provided and valid, enrich and validate it.
    Otherwise, construct deterministic, grounded comparison rows.
    """
    title_a = product_a.get("title") or "Product 1"
    title_b = product_b.get("title") or "Product 2"
    brand_a = product_a.get("brand") or "Not available in catalog"
    brand_b = product_b.get("brand") or "Not available in catalog"
    
    price_a_val = product_a.get("price_inr")
    price_b_val = product_b.get("price_inr")
    price_a = f"₹{Math_round(price_a_val)}" if price_a_val is not None else "Price unavailable"
    price_b = f"₹{Math_round(price_b_val)}" if price_b_val is not None else "Price unavailable"

    heading = f"Comparing {brand_a} vs {brand_b}" if brand_a != "Not available in catalog" and brand_b != "Not available in catalog" else f"Side-by-Side Comparison: Top 2 Products"

    # If Gemini returned valid structured rows, validate and fill missing honest values
    if gemini_comparison and gemini_comparison.rows and len(gemini_comparison.rows) >= 4:
        validated_rows = []
        for r in gemini_comparison.rows:
            aspect = r.aspect.strip()
            val_a = r.product_a.strip() if r.product_a else "Not available in catalog"
            val_b = r.product_b.strip() if r.product_b else "Not available in catalog"
            
            # Enforce exact prices
            if aspect.casefold() in ("price", "price (inr)", "pricing"):
                val_a = price_a
                val_b = price_b
            elif aspect.casefold() in ("brand", "manufacturer"):
                val_a = brand_a
                val_b = brand_b
            elif aspect.casefold() in ("product name", "title", "product"):
                val_a = title_a
                val_b = title_b

            validated_rows.append(ComparisonRow(aspect=aspect, product_a=val_a, product_b=val_b))

        # Ensure extracted factual category specs are preserved in comparison rows
        existing_aspects = {r.aspect.casefold() for r in validated_rows}
        specs_a = extract_product_specs(product_a, category)
        specs_b = extract_product_specs(product_b, category)
        for spec_name in ["RAM", "Storage", "Battery", "Display", "Connectivity", "Noise Cancellation"]:
            if (spec_name in specs_a or spec_name in specs_b) and spec_name.casefold() not in existing_aspects:
                validated_rows.append(ComparisonRow(
                    aspect=spec_name,
                    product_a=specs_a.get(spec_name, "Not available in catalog"),
                    product_b=specs_b.get(spec_name, "Not available in catalog"),
                ))

        conclusion = gemini_comparison.conclusion or (
            f"Both products offer distinct advantages. {title_a} suits shoppers seeking {product_a.get('explanation', 'strong value')}, "
            f"while {title_b} is tailored for {product_b.get('explanation', 'alternative performance priorities')}."
        )

        return ComparisonData(
            heading=gemini_comparison.heading or heading,
            product_a_asin=product_a.get("asin"),
            product_b_asin=product_b.get("asin"),
            rows=validated_rows,
            conclusion=conclusion,
        )

    # Deterministic generation
    specs_a = extract_product_specs(title_a, category)
    specs_b = extract_product_specs(title_b, category)

    rows: list[ComparisonRow] = [
        ComparisonRow(aspect="Product Name", product_a=title_a, product_b=title_b),
        ComparisonRow(aspect="Price", product_a=price_a, product_b=price_b),
        ComparisonRow(aspect="Brand", product_a=brand_a, product_b=brand_b),
    ]

    # Category-specific rows
    cat_norm = (category or "").casefold()
    if "phone" in cat_norm:
        rows.append(ComparisonRow(
            aspect="RAM & Storage",
            product_a=f"{specs_a.get('RAM', 'Not specified')} / {specs_a.get('Storage', 'Not specified')}" if (specs_a.get('RAM') or specs_a.get('Storage')) else "Not available in catalog",
            product_b=f"{specs_b.get('RAM', 'Not specified')} / {specs_b.get('Storage', 'Not specified')}" if (specs_b.get('RAM') or specs_b.get('Storage')) else "Not available in catalog",
        ))
        rows.append(ComparisonRow(
            aspect="Battery & Display",
            product_a=f"{specs_a.get('Battery', 'Not specified')} / {specs_a.get('Display', 'Not specified')}" if (specs_a.get('Battery') or specs_a.get('Display')) else "Not available in catalog",
            product_b=f"{specs_b.get('Battery', 'Not specified')} / {specs_b.get('Display', 'Not specified')}" if (specs_b.get('Battery') or specs_b.get('Display')) else "Not available in catalog",
        ))
    elif "electron" in cat_norm or "headphone" in cat_norm:
        rows.append(ComparisonRow(
            aspect="Connectivity & Audio",
            product_a=specs_a.get("Connectivity") or specs_a.get("Noise Cancellation") or "Not available in catalog",
            product_b=specs_b.get("Connectivity") or specs_b.get("Noise Cancellation") or "Not available in catalog",
        ))
        rows.append(ComparisonRow(
            aspect="Battery / Playtime",
            product_a=specs_a.get("Battery") or "Not available in catalog",
            product_b=specs_b.get("Battery") or "Not available in catalog",
        ))
    elif "home" in cat_norm or "kitchen" in cat_norm:
        rows.append(ComparisonRow(
            aspect="Material & Design",
            product_a=next((f for f in product_a.get("key_factors", []) if "material" in f.lower() or "non-stick" in f.lower() or "steel" in f.lower()), "Not available in catalog"),
            product_b=next((f for f in product_b.get("key_factors", []) if "material" in f.lower() or "non-stick" in f.lower() or "steel" in f.lower()), "Not available in catalog"),
        ))
    elif "cloth" in cat_norm or "shoe" in cat_norm or "jewelry" in cat_norm:
        rows.append(ComparisonRow(
            aspect="Design & Material",
            product_a=next((f for f in product_a.get("key_factors", []) if "durable" in f.lower() or "cotton" in f.lower() or "waterproof" in f.lower()), "Not available in catalog"),
            product_b=next((f for f in product_b.get("key_factors", []) if "durable" in f.lower() or "cotton" in f.lower() or "waterproof" in f.lower()), "Not available in catalog"),
        ))
    elif "office" in cat_norm:
        rows.append(ComparisonRow(
            aspect="Ergonomics & Adjustment",
            product_a=next((f for f in product_a.get("key_factors", []) if "ergonomic" in f.lower() or "comfort" in f.lower()), "Not available in catalog"),
            product_b=next((f for f in product_b.get("key_factors", []) if "ergonomic" in f.lower() or "comfort" in f.lower()), "Not available in catalog"),
        ))
    elif "sport" in cat_norm:
        rows.append(ComparisonRow(
            aspect="Performance & Activity",
            product_a=next((f for f in product_a.get("key_factors", []) if "running" in f.lower() or "training" in f.lower() or "cushion" in f.lower()), "Not available in catalog"),
            product_b=next((f for f in product_b.get("key_factors", []) if "running" in f.lower() or "training" in f.lower() or "cushion" in f.lower()), "Not available in catalog"),
        ))
    else:
        # General key specs
        spec_summary_a = ", ".join(f"{k}: {v}" for k, v in specs_a.items()) if specs_a else "Not available in catalog"
        spec_summary_b = ", ".join(f"{k}: {v}" for k, v in specs_b.items()) if specs_b else "Not available in catalog"
        rows.append(ComparisonRow(aspect="Key Specifications", product_a=spec_summary_a, product_b=spec_summary_b))

    # Evidence / sentiment / strengths / limitations / suited for
    factors_a = product_a.get("key_factors") or []
    factors_b = product_b.get("key_factors") or []

    rows.extend([
        ComparisonRow(
            aspect="Customer Sentiment",
            product_a=", ".join(factors_a[:2]) if factors_a else "Positive customer reception in catalog reviews",
            product_b=", ".join(factors_b[:2]) if factors_b else "Positive customer reception in catalog reviews",
        ),
        ComparisonRow(
            aspect="Main Strengths",
            product_a=product_a.get("explanation") or (factors_a[0] if factors_a else "Strong category relevance"),
            product_b=product_b.get("explanation") or (factors_b[0] if factors_b else "Strong category relevance"),
        ),
        ComparisonRow(
            aspect="Known Limitations",
            product_a="Higher price point" if (price_a_val and price_b_val and price_a_val > price_b_val * 1.3) else "Premium tier" if price_a_val and price_a_val > 25000 else "Standard catalog specifications",
            product_b="Higher price point" if (price_a_val and price_b_val and price_b_val > price_a_val * 1.3) else "Premium tier" if price_b_val and price_b_val > 25000 else "Standard catalog specifications",
        ),
        ComparisonRow(
            aspect="Best Suited For",
            product_a=f"Shoppers prioritizing {brand_a} and {product_a.get('explanation', 'reliable performance')}",
            product_b=f"Shoppers prioritizing {brand_b} and {product_b.get('explanation', 'balanced features')}",
        ),
    ])

    conclusion = (
        f"Comparing these two options: {title_a} ({price_a}) stands out for {product_a.get('explanation', 'its primary strengths')}, "
        f"whereas {title_b} ({price_b}) is better suited if you prioritize {product_b.get('explanation', 'its distinctive factors')}."
    )

    return ComparisonData(
        heading=heading,
        product_a_asin=product_a.get("asin"),
        product_b_asin=product_b.get("asin"),
        rows=rows,
        conclusion=conclusion,
    )


def Math_round(val: Optional[float]) -> str:
    if val is None:
        return ""
    try:
        return f"{int(round(val)):,}"
    except (ValueError, TypeError):
        return str(val)
