"""
Incident Triage Agent — FastAPI app.

Day 19: /triage endpoint accepts a real request body but returns a
hardcoded response. The endpoint signature and response shape stay
stable from this point on — Day 20-21 only swap out the function body.
"""

from fastapi import FastAPI
from app.schemas import IncidentRequest, TriageResponse

app = FastAPI(
    title="Incident Triage Agent",
    description="RAG-based incident triage suggestions. Status: in active development.",
    version="0.0.2",
)


@app.get("/")
def root():
    """Service identity. Useful for sanity-checking deploys."""
    return {
        "service": "incident-triage-agent",
        "status": "alive",
        "version": "0.0.2",
    }


@app.get("/health")
def health():
    """Liveness probe. Always returns 200 OK if the process is up."""
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage(request: IncidentRequest) -> TriageResponse:
    """
    Suggest a triage (severity, category, action) for an incoming incident.

    Day 19: returns a hardcoded response regardless of input.
    Day 20: will embed the request and retrieve similar past incidents.
    Day 21: will pass retrieval + request to an LLM for a real suggestion.
    """
    # TODO(Day 20): embed request.description and retrieve top-k from Chroma.
    # TODO(Day 21): pass retrieved incidents + request to LLM, parse response.

    return TriageResponse(
        severity="P3",
        category="performance",
        recommended_action="Acknowledge in #incidents, gather metrics for the affected service, "
                           "page the service owner if error rate exceeds 1%.",
        reasoning="Hardcoded stub response — real retrieval-augmented logic lands Day 20-21.",
        similar_incidents=[],
    )
