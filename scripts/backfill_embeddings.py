import sys
import os

# Add the project root to the python path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Item
from app.search_utils import generate_embedding


def backfill_embeddings():
    app = create_app()
    with app.app_context():
        items = Item.query.all()
        print(f"Found {len(items)} items to process.")

        count = 0
        for item in items:
            if item.embedding is None:
                print(f"Generating embedding for item {item.id}: {item.title}")
                # Combine title and description for embedding
                text = f"{item.title} {item.description or ''}"
                item.embedding = generate_embedding(text)
                count += 1
            else:
                print(f"Item {item.id} already has embedding. Skipping.")

        if count > 0:
            db.session.commit()
            print(f"Successfully generated embeddings for {count} items.")
        else:
            print("No items needed updates.")


if __name__ == "__main__":
    backfill_embeddings()
