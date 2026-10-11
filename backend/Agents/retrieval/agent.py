
from typing import Optional
import re

from ..query_understanding import QueryUnderstanding
from backend.pipeline.retrieval import ProductRetriever

from .schema import RetrievalResult, RetrievedProduct


class RetrievalAgent:
    """Retrieve and prioritize relevant retail products."""

    FETCH_MULTIPLIER = 5
    MAX_FETCH = 50
    TITLE_FETCH_LIMIT = 100

    PRODUCT_TYPE_ALIASES = {
        "phone": [
            "phone", "smartphone", "mobile phone", "cell phone",
        ],
        "headphones": [
            "headphone", "headphones", "headset",
            "earphone", "earphones", "earbud", "earbuds",
        ],
        "cookware set": [
            "cookware set", "pots and pans", "cooking set",
        ],
        "jacket": [
            "jacket", "coat", "parka", "windbreaker",
        ],
        "office chair": [
            "office chair", "desk chair", "computer chair",
            "task chair", "ergonomic chair",
        ],
        "running shoes": [
            "running shoes", "running shoe",
            "trail running shoes", "trail running shoe",
            "athletic shoes", "athletic shoe",
            "jogging shoes", "jogging shoe",
            "running sneakers", "running sneaker",
        ],
    }

    PRODUCT_TYPE_EXCLUSIONS = {
        "phone": [
            "phone case", "phone cover", "replacement battery",
            "screen protector", "phone holder",
        ],
        "headphones": [
            "headphone stand", "headphone case",
            "replacement ear pads", "headphone cable",
        ],
        "cookware set": [
            "kitchen utensils", "spoon rest", "paper napkins",
            "cooking apron", "pot holder",
        ],
        "jacket": [
            "jacket hanger", "jacket zipper replacement",
        ],
        "office chair": [
            "chair cover", "chair mat", "chair wheels",
            "replacement caster", "chair cushion",
        ],
        "running shoes": [
            "running socks", "compression socks",
            "running gloves", "running top", "running shirt",
            "running shorts", "running jacket", "shoe laces",
            "shoelaces", "shoe insoles", "shoe cleaner",
            "replacement spikes",
        ],
    }

    def __init__(
        self,
        retriever: Optional[ProductRetriever] = None,
    ):
        self.retriever = retriever or ProductRetriever()

    def retrieve(
        self,
        query: QueryUnderstanding,
        top_k: int = 10,
    ) -> RetrievalResult:

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        semantic_text = self._build_semantic_query(query)
        where_filter = self._build_where_filter(query)

        fetch_k = min(
            max(top_k * self.FETCH_MULTIPLIER, top_k),
            self.MAX_FETCH,
        )

        semantic_results = self.retriever.search(
            query=semantic_text,
            top_k=fetch_k,
            where=where_filter or None,
        )

        title_results = []

        if query.product_type:
            title_results = self.retriever.search_by_title_terms(
                terms=self._get_product_type_terms(
                    query.product_type
                ),
                where=where_filter or None,
                max_results=self.TITLE_FETCH_LIMIT,
            )

        # Deduplicate by product ID, preserving semantic distances
        # whenever a product was returned by semantic search.
        merged = {
            item["asin"]: item
            for item in semantic_results
        }

        for item in title_results:
            merged.setdefault(item["asin"], item)

        candidates = list(merged.values())

        # Exclude clear product-type mismatches, then rank candidates.
        scored_candidates = [
            (
                item,
                self._product_type_score(
                    item, query.product_type
                ),
            )
            for item in candidates
        ]

        if query.product_type:
            matching_candidates = [
                (item, score)
                for item, score in scored_candidates
                if score >= 1
            ]

            # Use strict title/document matching when enough candidates exist.
            if len(matching_candidates) >= top_k:
                scored_candidates = matching_candidates

        # Product-type score is the primary signal;
        # semantic distance breaks ties between equally matched products.
        scored_candidates.sort(
            key=lambda pair: (
                -pair[1],
                pair[0]["distance"],
            )
        )

        selected = [
            item for item, score in scored_candidates[:top_k]
        ]

        products = [
            self._to_retrieved_product(item, query)
            for item in selected
        ]

        return RetrievalResult(
            query_text_used=semantic_text,
            hard_filters_applied=where_filter,
            hard_constraints_not_enforced=list(
                query.hard_constraints
            ),
            total_candidates_returned=len(products),
            products=products,
        )

    def _get_product_type_terms(
        self,
        product_type: str,
    ) -> list[str]:

        normalized = product_type.casefold().strip()

        aliases = self.PRODUCT_TYPE_ALIASES.get(
            normalized, [normalized]
        )

        return list(dict.fromkeys(aliases))

    def _build_semantic_query(
        self,
        query: QueryUnderstanding,
    ) -> str:

        parts = [query.raw_query]

        if query.product_type:
            parts.append(query.product_type)

        parts.extend(query.quality_tags)
        parts.extend(query.hard_constraints)

        return " ".join(dict.fromkeys(
            part.strip()
            for part in parts
            if part and part.strip()
        ))

    def _build_where_filter(
        self,
        query: QueryUnderstanding,
    ) -> dict:

        conditions = []

        if query.category is not None:
            category = getattr(
                query.category, "value", query.category
            )
            conditions.append({
                "main_category": {"$eq": category}
            })

        if query.budget_min is not None:
            conditions.append({
                "price_inr": {"$gte": query.budget_min}
            })

        if query.budget_max is not None:
            conditions.append({
                "price_inr": {"$lte": query.budget_max}
            })

        if query.brand.preferred:
            preferred = {
                brand.strip().casefold()
                for brand in query.brand.preferred
                if brand and brand.strip()
            }

            variants = {
                "samsung": ["Samsung", "SAMSUNG"],
            }

            expanded = set()

            for brand in preferred:
                expanded.update(
                    variants.get(brand, [brand])
                )

            conditions.append({
                "brand": {"$in": sorted(expanded)}
            })

        if query.brand.excluded:
            excluded = [
                brand.strip()
                for brand in query.brand.excluded
                if brand and brand.strip()
            ]

            if excluded:
                conditions.append({
                    "brand": {"$nin": excluded}
                })

        if not conditions:
            return {}

        if len(conditions) == 1:
            return conditions[0]

        return {"$and": conditions}

    @staticmethod
    def _contains_phrase(text: str, phrase: str) -> bool:
        pattern = (
            r"(?<!\w)"
            + re.escape(phrase.casefold())
            + r"(?!\w)"
        )
        return re.search(pattern, text.casefold()) is not None

    def _product_type_score(
        self,
        item: dict,
        product_type: Optional[str],
    ) -> int:
        if not product_type:
            return 0

        metadata = item.get("metadata") or {}
        title = str(metadata.get("title") or "").casefold().strip()
        document = str(item.get("document") or "").casefold()

        if not title:
            return 0

        normalized = product_type.casefold().strip()

        aliases = self.PRODUCT_TYPE_ALIASES.get(
            normalized, [normalized]
        )
        exclusions = self.PRODUCT_TYPE_EXCLUSIONS.get(
            normalized, []
        )

        # Exclude accessories and unrelated products first.
        if any(
            self._contains_phrase(title, term.casefold())
            for term in exclusions
        ):
            return -2

        # Strongest match: the title starts with a product-type alias.
        if any(
            title.startswith(alias.casefold())
            for alias in aliases
        ):
            return 3

        # Strong match: product type appears in the title.
        if any(
            self._contains_phrase(title, alias.casefold())
            for alias in aliases
        ):
            return 2

        # Weak match: product type appears only in the document.
        if any(
            self._contains_phrase(document, alias.casefold())
            for alias in aliases
        ):
            return 1

        return 0

    @staticmethod
    def _extract_specifications(title: str) -> dict:
        """
        Conservatively extract specifications explicitly written
        in a product title. Missing or ambiguous values stay None.
        """
        text = title.casefold()

        specs = {
            "ram_gb": None,
            "storage_gb": None,
            "camera_mp": None,
            "battery_mah": None,
        }

        # RAM: e.g. "8GB RAM", "8 GB RAM", "4GB RAM".
        ram_matches = re.findall(
            r"\b(\d+(?:\.\d+)?)\s*gb\s*(?:of\s*)?ram\b",
            text,
        )

        if ram_matches:
            values = {float(value) for value in ram_matches}
            if len(values) == 1:
                specs["ram_gb"] = values.pop()

        # Storage: e.g. "128GB storage", "256 GB ROM".
        storage_matches = re.findall(
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(gb|tb)\s*(?:internal\s*)?"
            r"(?:storage|rom)\b",
            text,
        )

        storage_values = {
            float(value) * (1024 if unit == "tb" else 1)
            for value, unit in storage_matches
        }

        if len(storage_values) == 1:
            specs["storage_gb"] = storage_values.pop()

        # Camera: e.g. "50MP camera", "12 MP rear camera".
        camera_matches = re.findall(
            r"\b(\d+(?:\.\d+)?)\s*mp\s*"
            r"(?:rear\s*|front\s*)?camera\b",
            text,
        )

        if camera_matches:
            camera_values = {
                float(value) for value in camera_matches
            }
            if len(camera_values) == 1:
                specs["camera_mp"] = camera_values.pop()

        # Battery: e.g. "5000mAh battery".
        battery_matches = re.findall(
            r"\b(\d{3,6})\s*mah\b",
            text,
        )

        if battery_matches:
            battery_values = {
                float(value) for value in battery_matches
            }
            if len(battery_values) == 1:
                specs["battery_mah"] = battery_values.pop()

        return specs

    @staticmethod
    def _meets_threshold(
        value: Optional[float],
        threshold: Optional[float],
    ) -> Optional[bool]:

        if threshold is None or value is None:
            return None

        return value >= threshold

    def _to_retrieved_product(
        self,
        item: dict,
        query: QueryUnderstanding,
    ) -> RetrievedProduct:

        metadata = item.get("metadata") or {}
        title = str(metadata.get("title") or "Unknown")
        requested = query.specs

        title_specs = self._extract_specifications(title)

        # Prefer structured metadata; use title extraction only
        # when structured metadata is absent.
        ram = metadata.get("ram_gb")
        storage = metadata.get("storage_gb")
        camera = metadata.get("camera_mp")
        battery = metadata.get("battery_mah")

        if ram is None:
            ram = title_specs["ram_gb"]
        if storage is None:
            storage = title_specs["storage_gb"]
        if camera is None:
            camera = title_specs["camera_mp"]
        if battery is None:
            battery = title_specs["battery_mah"]

        return RetrievedProduct(
            asin=item["asin"],
            title=title,
            brand=metadata.get("brand"),
            price_inr=metadata.get("price_inr"),

            ram_gb=ram,
            storage_gb=storage,
            camera_mp=camera,
            battery_mah=battery,

            average_rating=metadata.get("average_rating"),
            total_reviews=metadata.get("review_count"),
            average_sentiment_score=metadata.get(
                "average_sentiment"
            ),
            positive_ratio=metadata.get("positive_ratio"),
            negative_ratio=metadata.get("negative_ratio"),

            distance=float(item["distance"]),

            meets_ram=self._meets_threshold(
                ram, requested.ram_gb
            ),
            meets_storage=self._meets_threshold(
                storage, requested.storage_gb
            ),
            meets_camera=self._meets_threshold(
                camera, requested.camera_mp_min
            ),
            meets_battery=self._meets_threshold(
                battery, requested.battery_mah_min
            ),

            camera_sentiment=metadata.get("sentiment_camera"),
            battery_sentiment=metadata.get("sentiment_battery"),
            performance_sentiment=metadata.get(
                "sentiment_performance"
            ),
            display_sentiment=metadata.get("sentiment_display"),
            value_sentiment=metadata.get("sentiment_value"),

            camera_mentions=None,
            battery_mentions=None,
            performance_mentions=None,
            display_mentions=None,
            value_mentions=None,
        )
