
import chromadb
from FlagEmbedding import BGEM3FlagModel


CHROMA_PATH = "data/chromadb"
COLLECTION_NAME = "retail_products"
MODEL_NAME = "BAAI/bge-m3"


class ProductRetriever:
    """Retrieve products through semantic and title-based search."""

    def __init__(self):
        print("Initializing Product Retriever...")

        self.model = BGEM3FlagModel(
            MODEL_NAME,
            use_fp16=False,
        )

        self.client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )

        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

        print(
            f"Connected to ChromaDB. "
            f"Products available: {self.collection.count()}"
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
        where: dict | None = None,
    ):
        """Retrieve semantically similar products."""

        if top_k < 1:
            raise ValueError("top_k must be at least 1")

        query_embedding = self.model.encode(
            [query],
            batch_size=1,
            max_length=512,
        )["dense_vecs"][0]

        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k,
            where=where,
            include=[
                "metadatas",
                "documents",
                "distances",
            ],
        )

        products = []

        for product_id, metadata, document, distance in zip(
            results["ids"][0],
            results["metadatas"][0],
            results["documents"][0],
            results["distances"][0],
        ):
            products.append({
                "asin": product_id,
                "metadata": metadata or {},
                "document": document or "",
                "distance": float(distance),
            })

        return products

    def search_by_title_terms(
        self,
        terms: list[str],
        where: dict | None = None,
        max_results: int = 100,
        batch_size: int = 1000,
    ):
        """
        Find products whose stored titles contain any requested term.

        This scans catalog metadata in batches because title substring
        matching is performed in Python, not through an unsupported
        ChromaDB metadata substring filter.

        Results are limited to max_results. This is a targeted
        fallback, not a guarantee of exhaustive product discovery.
        """

        if max_results < 1 or not terms:
            return []

        normalized_terms = [
            term.strip().casefold()
            for term in terms
            if term and term.strip()
        ]

        if not normalized_terms:
            return []

        products = []
        offset = 0

        while len(products) < max_results:
            batch = self.collection.get(
                where=where,
                limit=batch_size,
                offset=offset,
                include=["metadatas", "documents"],
            )

            ids = batch.get("ids", [])
            metadatas = batch.get("metadatas") or []
            documents = batch.get("documents") or []

            if not ids:
                break

            for product_id, metadata, document in zip(
                ids,
                metadatas,
                documents,
            ):
                metadata = metadata or {}
                title = str(metadata.get("title") or "")
                title_lower = title.casefold()

                if any(
                    term in title_lower
                    for term in normalized_terms
                ):
                    products.append({
                        "asin": product_id,
                        "metadata": metadata,
                        "document": document or "",
                        # A title-only candidate has no semantic
                        # distance from this query.
                        "distance": 1.0,
                    })

                    if len(products) >= max_results:
                        break

            offset += len(ids)

        return products
