
from backend.pipeline.retrieval import ProductRetriever


def main():
    retriever = ProductRetriever()

    print("=" * 70)
    print("RUNNING SHOES CATALOG DIAGNOSTIC")
    print("=" * 70)

    offset = 0
    batch_size = 1000
    total_scanned = 0
    matches = []

    search_terms = [
        "running shoes",
        "trail running shoes",
        "athletic shoe",
        "jogging shoe",
        "running sneaker",
    ]

    while True:
        batch = retriever.collection.get(
            where={
                "main_category": "Sports_and_Outdoors"
            },
            limit=batch_size,
            offset=offset,
            include=["metadatas"],
        )

        ids = batch.get("ids", [])
        metadatas = batch.get("metadatas") or []

        if not ids:
            break

        total_scanned += len(ids)

        for metadata in metadatas:
            title = str(metadata.get("title") or "")
            title_lower = title.casefold()

            if any(term in title_lower for term in search_terms):
                if len(matches) < 30:
                    matches.append(title)

        offset += len(ids)

    print(f"\nProducts scanned: {total_scanned}")
    print(f"Matching titles displayed: {len(matches)}")

    for index, title in enumerate(matches, start=1):
        print(f"{index}. {title}")

    if not matches:
        print(
            "\nNo titles matched these exact phrases. "
            "Other wording may still identify running shoes."
        )


if __name__ == "__main__":
    main()
