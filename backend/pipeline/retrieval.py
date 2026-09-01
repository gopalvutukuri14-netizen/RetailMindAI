import chromadb
from FlagEmbedding import BGEM3FlagModel


# -----------------------------
# Configuration
# -----------------------------

CHROMA_PATH = "data/chromadb"
COLLECTION_NAME = "retail_products"
MODEL_NAME = "BAAI/bge-m3"


class ProductRetriever:
    """
    Handles semantic product retrieval using
    BGE-M3 embeddings and ChromaDB.
    """

    def __init__(self):

        print("Initializing Product Retriever...")

        # Load embedding model
        self.model = BGEM3FlagModel(
            MODEL_NAME,
            use_fp16=False
        )

        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(
            path=CHROMA_PATH
        )

        # Load collection
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME
        )

        print(
            f"Connected to ChromaDB. "
            f"Products available: {self.collection.count()}"
        )


    def search(self, query: str, top_k: int = 20, where: dict | None = None):
        """
        Convert the query into an embedding and
        retrieve the most semantically similar products.
        """

        # Generate query embedding
        query_embedding = self.model.encode(
            [query],
            batch_size=1,
            max_length=512
        )["dense_vecs"][0]


        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[
                query_embedding.tolist()
            ],
            n_results=top_k,
            where=where,
            include=[
                "metadatas",
                "documents",
                "distances"
            ]
        )


        # Convert ChromaDB result into
        # easier-to-use Python objects
        products = []

        ids = results["ids"][0]
        metadatas = results["metadatas"][0]
        documents = results["documents"][0]
        distances = results["distances"][0]


        for product_id, metadata, document, distance in zip(
            ids,
            metadatas,
            documents,
            distances
        ):

            product = {
                "asin": product_id,
                "metadata": metadata,
                "document": document,
                "distance": float(distance)
            }

            products.append(product)


        return products