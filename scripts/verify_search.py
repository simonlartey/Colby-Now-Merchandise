import sys
import os

# Add the project root to the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app
from app.models import Item


def verify_search():
    app = create_app()
    with app.app_context():
        queries = [
            "gaming accessory",
            "warm clothes",
            "computer book",
            "cold drink storage",
            "tablet",
            "nonsense gibberish 123",  # Should return empty
        ]

        print("\n--- Semantic Search Verification (Threshold: 0.25) ---\n")

        for query in queries:
            print(f"Query: '{query}'")
            results = Item.semantic_search(query, limit=5)
            if not results:
                print("  No results found (Correct for irrelevant queries).")
            for i, item in enumerate(results):
                # We can't easily get the score here without modifying return, but that's fine.
                # The fact they are returned means score >= 0.25
                print(f"  {i+1}. {item.title} (${item.price})")
            print("")


if __name__ == "__main__":
    verify_search()
