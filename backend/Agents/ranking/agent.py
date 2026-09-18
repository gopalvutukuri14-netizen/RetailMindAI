from typing import Optional

from .schema import RankingResult, RankedProduct, ScoreBreakdown


DEFAULT_WEIGHTS = {
    "similarity": 0.30,
    "spec_match": 0.20,
    "sentiment": 0.15,
    "aspect_alignment": 0.25,
    "memory_alignment": 0.10,
}

TAG_TO_ASPECT = {
    "camera": ["camera", "photo", "picture", "selfie"],
    "battery": ["battery", "charge"],
    "performance": ["performance", "fast", "speed", "gaming", "smooth", "lag"],
    "display": ["display", "screen"],
    "value": ["price", "value", "cheap", "affordable", "budget"],
}

ASPECT_PRAISE_THRESHOLD = {
    "camera": 0.4,
    "battery": 0.2,
    "performance": 0.3,
    "display": 0.35,
    "value": 0.4,
}


class RankingAgent:
    def __init__(self, weights: Optional[dict] = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def rank(self, query, retrieval_result, profile=None) -> RankingResult:
        memory_applied = self._profile_has_signal(profile)
        ranked = []
        for product in retrieval_result.products:
            breakdown = self._score_product(query, product, profile if memory_applied else None)
            reasons = self._build_reasons(query, product, profile if memory_applied else None, breakdown)
            ranked.append(
                RankedProduct(
                    asin=product.asin, title=product.title, brand=product.brand,
                    price_inr=product.price_inr, scores=breakdown, match_reasons=reasons,
                )
            )
        ranked.sort(key=lambda p: p.scores.final_score, reverse=True)
        return RankingResult(
            user_id=profile.user_id if memory_applied else None,
            memory_applied=memory_applied, total_ranked=len(ranked), products=ranked,
        )

    def _score_product(self, query, product, profile) -> ScoreBreakdown:
        similarity = self._similarity_score(product.distance)
        spec_match = self._spec_match_score(query, product)
        sentiment = self._sentiment_score(product.average_sentiment_score)
        aspect_alignment = self._aspect_alignment_score(query, product)
        memory_alignment = self._memory_alignment_score(query, product, profile)
        raw_scores = {
            "similarity": similarity, "spec_match": spec_match, "sentiment": sentiment,
            "aspect_alignment": aspect_alignment, "memory_alignment": memory_alignment,
        }
        final = self._weighted_average(raw_scores)
        return ScoreBreakdown(
            similarity_score=similarity, spec_match_score=spec_match, sentiment_score=sentiment,
            aspect_alignment_score=aspect_alignment, memory_alignment_score=memory_alignment,
            final_score=final,
        )

    def _weighted_average(self, raw_scores: dict) -> float:
        available = {k: v for k, v in raw_scores.items() if v is not None}
        if not available:
            return 0.5
        total_weight = sum(self.weights[k] for k in available)
        return sum(self.weights[k] * v for k, v in available.items()) / total_weight

    def _similarity_score(self, distance: float) -> Optional[float]:
        if distance is None:
            return None
        return max(0.0, min(1.0, 1 - (distance / 2)))

    def _spec_match_score(self, query, product) -> Optional[float]:
        checks = [
            (query.specs.ram_gb, product.meets_ram),
            (query.specs.storage_gb, product.meets_storage),
            (query.specs.camera_mp_min, product.meets_camera),
            (query.specs.battery_mah_min, product.meets_battery),
        ]
        applicable = [meets for asked, meets in checks if asked is not None and meets is not None]
        if not applicable:
            return None
        return sum(1 for m in applicable if m) / len(applicable)

    def _sentiment_score(self, average_sentiment_score) -> Optional[float]:
        if average_sentiment_score is None:
            return None
        return max(0.0, min(1.0, (average_sentiment_score + 1) / 2))

    def _matched_aspects(self, quality_tags: list) -> set:
        matched = set()
        for tag in quality_tags:
            lowered = tag.lower()
            for aspect, keywords in TAG_TO_ASPECT.items():
                if any(kw in lowered for kw in keywords):
                    matched.add(aspect)
        return matched

    def _aspect_alignment_score(self, query, product) -> Optional[float]:
        aspects = self._matched_aspects(query.quality_tags)
        if not aspects:
            return None
        scores = []
        for aspect in aspects:
            raw = getattr(product, f"{aspect}_sentiment", None)
            if raw is not None:
                scores.append(max(0.0, min(1.0, (raw + 1) / 2)))
        if not scores:
            return None
        return sum(scores) / len(scores)

    def _memory_alignment_score(self, query, product, profile) -> Optional[float]:
        if profile is None:
            return None
        components = []
        if profile.excluded_brands and product.brand and product.brand in profile.excluded_brands:
            components.append(0.0)
        elif profile.preferred_brands:
            components.append(1.0 if product.brand in profile.preferred_brands else 0.0)
        if profile.typical_budget_max is not None and product.price_inr is not None:
            within_budget = product.price_inr <= profile.typical_budget_max
            if profile.typical_budget_min is not None:
                within_budget = within_budget and product.price_inr >= profile.typical_budget_min
            components.append(1.0 if within_budget else 0.0)
        if profile.recurring_quality_tags and query.quality_tags:
            recurring = set(t.lower() for t in profile.recurring_quality_tags)
            current = set(t.lower() for t in query.quality_tags)
            components.append(len(recurring & current) / len(recurring))
        if not components:
            return None
        return sum(components) / len(components)

    def _build_reasons(self, query, product, profile, breakdown: ScoreBreakdown) -> list:
        reasons = []
        if breakdown.spec_match_score == 1.0:
            reasons.append("Meets all specified requirements")
        aspects = self._matched_aspects(query.quality_tags)
        for aspect in aspects:
            raw = getattr(product, f"{aspect}_sentiment", None)
            mentions = getattr(product, f"{aspect}_mentions", 0) or 0
            if raw is not None and raw >= ASPECT_PRAISE_THRESHOLD[aspect] and mentions >= 3:
                reasons.append(f"Customers specifically praise the {aspect} ({mentions} mentions)")
            elif raw is not None and raw < 0 and mentions >= 3:
                reasons.append(f"Some customers report issues with the {aspect}")
        if profile is not None and profile.preferred_brands and product.brand in profile.preferred_brands:
            reasons.append(f"Matches your usual preferred brand ({product.brand})")
        return reasons

    def _profile_has_signal(self, profile) -> bool:
        if profile is None:
            return False
        return bool(
            profile.preferred_brands or profile.excluded_brands
            or profile.typical_budget_min is not None or profile.typical_budget_max is not None
            or profile.recurring_quality_tags
        )