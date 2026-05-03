"""
Incident Triage Agent — FastAPI app.

Day 21: /triage now runs the real RAG flow. Hardcoded response is gone.
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from app.schemas import IncidentRequest, TriageResponse
from app import triage
from app.llm import LLMError

app = FastAPI(
    title="Incident Triage Agent",
    description="RAG-based incident triage suggestions. Status: in active development.",
    version="0.0.3",
)


@app.get("/")
def root():
    """Service identity. Useful for sanity-checking deploys."""
    return {
        "service": "incident-triage-agent",
        "status": "alive",
        "version": "0.0.3",
    }


@app.get("/health")
def health():
    """Liveness probe. Always returns 200 OK if the process is up."""
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResponse)
def triage_endpoint(request: IncidentRequest) -> TriageResponse:
    """
    Suggest a triage (severity, category, action) for an incoming incident.

    Pipeline:
      1. Embed the description, retrieve top-3 similar past incidents
      2. Build prompt with retrieved incidents as grounded context
      3. Call gpt-4o-mini with structured-output constraint to TriageResponse
      4. Return the validated response
    """
    try:
        return triage.run(request)
    except LLMError as e:
        # LLM unreachable, refused, or returned unparseable output.
        # 503 because this is a transient upstream-dependency failure,
        # not a client error — the request itself was valid.
        raise HTTPException(status_code=503, detail=f"Triage service unavailable: {e}")