"""
One-time script: load the incident corpus from data/incidents.json,
embed it, and store it in the Chroma collection.

Run from project root:
    python scripts/seed_corpus.py

Idempotent-ish: re-running will add duplicate IDs (Chroma will error).
To re-seed, delete the chroma_db/ directory first.
"""

import json
from pathlib import Path
from dotenv import load_dotenv

# Load .env BEFORE importing app modules — they need OPENAI_API_KEY.
load_dotenv()

from app.vector_store import add_incidents, get_collection


def main():
    corpus_path = Path("data/incidents.json")
    incidents = json.loads(corpus_path.read_text())

    print(f"Loaded {len(incidents)} incidents from {corpus_path}")

    # Sanity check — what's already there?
    collection = get_collection()
    existing_count = collection.count()
    if existing_count > 0:
        print(f"Collection already has {existing_count} documents. "
              f"Delete chroma_db/ to re-seed cleanly.")
        return

    print(f"Embedding {len(incidents)} incidents (one batched API call)...")
    add_incidents(incidents)

    final_count = collection.count()
    print(f"Done. Collection now has {final_count} documents.")


if __name__ == "__main__":
    main()