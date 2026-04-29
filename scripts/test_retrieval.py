"""
Manual smoke test for retrieval. Run from project root:

    python scripts/test_retrieval.py
"""

from dotenv import load_dotenv

load_dotenv()

from app.vector_store import retrieve_similar


def main():
    queries = [
        "Our payment service is returning 500 errors to customers right now",
        "Database queries are taking 10x longer than usual after a deploy",
        "Found a public S3 bucket with customer data in it",
    ]

    for q in queries:
        print("=" * 80)
        print(f"QUERY: {q}")
        print("=" * 80)
        results = retrieve_similar(q, k=3)
        for i, r in enumerate(results, 1):
            print(f"\n  #{i}  {r['id']}  [{r['severity']} / {r['category']}]  "
                  f"distance={r['distance']:.3f}")
            print(f"      {r['title']}")
            print(f"      System: {r['system']}")
        print()


if __name__ == "__main__":
    main()