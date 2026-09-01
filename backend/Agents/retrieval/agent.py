from typing import Optional

from ..query_understanding import QueryUnderstanding
from backend.pipeline.retrieval import ProductRetriever

from .schema import RetrievalResult, RetrievedProduct


class RetrievalAgent:
    """
    Wraps ProductRetriever (semantic search over ChromaDB) and adds the
    structured filtering it doesn't do on its own.

    Deliberate design decisions (see full reasoning in project notes):
      1. Budget and brand are hard-filtered via ChromaDB metadata --
         missing data is low enough (~1-2%) that this is safe.
      2. RAM/storage/camera/battery are NOT hard-filtered -- 45-82% of
         this catalog is missing at least one spec, so a hard filter
         would silently discard good candidates. Each product is
         annotated with meets_* instead; Ranking Agent decides the weight.
      3. hard_constraints have no structured metadata field yet, so they
         are folded into the semantic query text as best-effort and
         explicitly reported as NOT enforced.
    """

    FETCH_MULTIPLIER = 3
    MAX_FETCH = 50

    def __init__(self, retriever: Optional[ProductRetriever] = None):
        # Accepts an injected retriever (e.g. for tests) so we don't
        # reload the embedding model on every instantiation.
        self.retriever = retriever or ProductRetriever()

    def retrieve(self, query: QueryUnderstanding, top_k: int = 10) -> RetrievalResult:
        semantic_text = self._build_semantic_query(query)
        where_filter = self._build_where_filter(query)
        fetch_k = min(top_k * self.FETCH_MULTIPLIER, self.MAX_FETCH)

        raw_results = self.retriever.search(
            query=semantic_text,
            top_k=fetch_k,
            where=where_filter or None,
        )

        products = [
            self._to_retrieved_product(item, query)
            for item in raw_results[:top_k]
        ]

        return RetrievalResult(
            query_text_used=semantic_text,
            hard_filters_applied=where_filter,
            hard_constraints_not_enforced=list(query.hard_constraints),
            total_candidates_returned=len(products),
            products=products,
        )

    def _build_semantic_query(self, query: QueryUnderstanding) -> str:
        parts = [query.raw_query]
        if query.quality_tags:
            parts.append(" ".join(query.quality_tags))
        if query.hard_constraints:
            parts.append(" ".join(query.hard_constraints))
        return " ".join(parts)

    def _build_where_filter(self, query: QueryUnderstanding) -> dict:
        conditions = []

        if query.budget_min is not None:
            conditions.append({"price_inr": {"$gte": query.budget_min}})
        if query.budget_max is not None:
            conditions.append({"price_inr": {"$lte": query.budget_max}})

        if query.brand.preferred:
            conditions.append({"brand": {"$in": query.brand.preferred}})
        if query.brand.excluded:
            conditions.append({"brand": {"$nin": query.brand.excluded}})

        if not conditions:
            return {}
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    def _to_retrieved_product(self, item: dict, query: QueryUnderstanding) -> RetrievedProduct:
        metadata = item["metadata"]
        specs = query.specs

        def meets(value_key, threshold):
            value = metadata.get(value_key)
            if value is None or threshold is None:
                return None
            return value >= threshold

        return RetrievedProduct(
            asin=item["asin"],
            title=metadata.get("title", "Unknown"),
            brand=metadata.get("brand"),
            price_inr=metadata.get("price_inr"),
            ram_gb=metadata.get("ram_gb"),
            storage_gb=metadata.get("storage_gb"),
            camera_mp=metadata.get("camera_mp"),
            battery_mah=metadata.get("battery_mah"),
            average_rating=metadata.get("average_rating"),
            total_reviews=metadata.get("total_reviews"),
            average_sentiment_score=metadata.get("average_sentiment_score"),
            positive_ratio=metadata.get("positive_ratio"),
            negative_ratio=metadata.get("negative_ratio"),
            distance=item["distance"],
            meets_ram=meets("ram_gb", specs.ram_gb),
            meets_storage=meets("storage_gb", specs.storage_gb),
            meets_camera=meets("camera_mp", specs.camera_mp_min),
            meets_battery=meets("battery_mah", specs.battery_mah_min),
        )