"""
Incident Triage Agent — entry point.

Day 18: hello-world only. Real /triage endpoint lands Day 19.
"""

from fastapi import FastAPI

app = FastAPI(
    title="Incident Triage Agent",
    description="RAG-based incident triage suggestions. Status: in active development.",
    version="0.0.1",
)


@app.get("/")
def root():
    """Service identity. Useful for sanity-checking deploys."""
    return {
        "service": "incident-triage-agent",
        "status": "alive",
        "version": "0.0.1",
    }


@app.get("/health")
def health():
    """Liveness probe. Always returns 200 OK if the process is up."""
    return {"status": "ok"}
