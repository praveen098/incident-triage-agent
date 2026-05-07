"""
Day 22 manual eval harness.

Hits the local /triage endpoint with a curated set of test queries
covering all 5 categories plus edge cases (no match, very short,
very long, ambiguous). Prints results and saves to test_outputs.json
for review and future README fodder.

Run from project root with the API server running:
    uvicorn app.main:app
    (in another terminal)
    python -m scripts.run_test_queries
"""

import json
import time
from pathlib import Path
import requests


API_URL = "http://localhost:8000/triage"

# 8 test queries. Curated to cover:
#   - All 5 categories (outage, security, performance, data_integrity, deployment_failure)
#   - Strong-match cases (close to a corpus incident)
#   - Weak-match cases (no good match in corpus)
#   - Length edge cases (very short, very long)
#   - Ambiguity (could go multiple ways)

TEST_QUERIES = [
    {
        "label": "outage_strong_match",
        "description": (
            "Our Stripe webhook integration started returning 502 errors about "
            "15 minutes ago. Roughly 40% of incoming webhooks failing. Customers "
            "reporting that payment confirmations are delayed."
        ),
        "expected_category": "outage",
        "notes": "Should match INC-002. P1 or P2 — customer-facing payments outage.",
    },
    {
        "label": "performance_post_deploy",
        "description": (
            "After deploying v3.2 of the search service this morning, p99 latency "
            "went from 80ms to 1200ms. Users reporting slow autocomplete. Error "
            "rate stable."
        ),
        "expected_category": "performance",
        "notes": "Should pull INC-001 (latency after deploy). P2 reasonable.",
    },
    {
        "label": "security_data_exposure",
        "description": (
            "Found out our user profile pictures S3 bucket has been public-readable "
            "for 2 hours due to a bad Terraform apply. Roughly 8000 profile pictures "
            "uploaded during the window."
        ),
        "expected_category": "security",
        "notes": "Should pull INC-012. P1 — data exposure.",
    },
    {
        "label": "data_integrity_dupe",
        "description": (
            "Customers reporting being charged twice for orders placed in the last "
            "hour. Initial check shows ~30 affected orders. Order service may have "
            "an idempotency issue."
        ),
        "expected_category": "data_integrity",
        "notes": "Should pull INC-010 (duplicate orders). P1 — financial impact.",
    },
    {
        "label": "deployment_failure",
        "description": (
            "Latest deploy of mobile API got stuck mid-rollout. Half the pods on "
            "v4.1, half on v4.2. Schema mismatch causing 5xx for users routed to "
            "old pods."
        ),
        "expected_category": "deployment_failure",
        "notes": "Should pull INC-007. P2 reasonable.",
    },
    {
        "label": "no_good_match",
        "description": (
            "Our internal Confluence wiki has been intermittently slow for 2 days. "
            "Page loads taking 8-15 seconds. Only affects employees, not customers. "
            "Vendor support ticket open."
        ),
        "expected_category": "performance",
        "notes": (
            "No strong corpus match — internal vendor tool. Should reason about "
            "this honestly and not invent a similar_incidents match. Likely P3/P4."
        ),
    },
    {
        "label": "very_short",
        "description": "Login broken for everyone.",
        "expected_category": "outage",
        "notes": (
            "Edge case: minimum-length input. Real on-call message style. "
            "Auth-related — should pull INC-003 or INC-023."
        ),
    },
    {
        "label": "ambiguous_security_or_outage",
        "description": (
            "API gateway returning 429s for ~15% of legitimate enterprise traffic "
            "since this morning. No deploy. Customers asking if we're under attack "
            "or if our rate limiter is misconfigured."
        ),
        "expected_category": "outage",
        "notes": (
            "Could pull INC-027 (rate limiter blocking enterprise) OR INC-023 (DDoS). "
            "Watch which one wins and whether the LLM acknowledges the ambiguity."
        ),
    },
]


def run_one(query: dict) -> dict:
    """POST one query, return enriched result with timing and metadata."""
    t0 = time.time()
    try:
        response = requests.post(
            API_URL,
            json={"description": query["description"]},
            timeout=60,
        )
        elapsed = time.time() - t0
        response.raise_for_status()
        return {
            "label": query["label"],
            "description": query["description"],
            "expected_category": query["expected_category"],
            "notes": query["notes"],
            "elapsed_seconds": round(elapsed, 2),
            "status_code": response.status_code,
            "response": response.json(),
        }
    except Exception as e:
        return {
            "label": query["label"],
            "description": query["description"],
            "expected_category": query["expected_category"],
            "notes": query["notes"],
            "elapsed_seconds": round(time.time() - t0, 2),
            "status_code": getattr(getattr(e, "response", None), "status_code", None),
            "error": str(e),
        }


def main():
    print(f"Running {len(TEST_QUERIES)} test queries against {API_URL}\n")
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/{len(TEST_QUERIES)}] {query['label']} ...", end=" ", flush=True)
        result = run_one(query)
        results.append(result)
        if "error" in result:
            print(f"ERROR ({result['elapsed_seconds']}s): {result['error']}")
        else:
            r = result["response"]
            print(
                f"{r['severity']}/{r['category']}  "
                f"sim={r['similar_incidents']}  "
                f"({result['elapsed_seconds']}s)"
            )

    out_path = Path("test_outputs.json")
    out_path.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {len(results)} results to {out_path}")

    # Summary table — easier to scan than the JSON
    print("\n" + "=" * 100)
    print(f"{'LABEL':<32} {'EXPECTED':<22} {'GOT':<22} {'SIM':<20}")
    print("=" * 100)
    for r in results:
        if "error" in r:
            print(f"{r['label']:<32} {r['expected_category']:<22} {'ERROR':<22} {'':<20}")
            continue
        resp = r["response"]
        got = f"{resp['severity']}/{resp['category']}"
        sim = ",".join(resp["similar_incidents"]) or "(none)"
        match = "✓" if resp["category"] == r["expected_category"] else "✗"
        print(f"{r['label']:<32} {r['expected_category']:<22} {got:<22} {sim:<20} {match}")


if __name__ == "__main__":
    main()