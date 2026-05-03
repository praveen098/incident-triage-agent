"""
Triage orchestration — the RAG flow.

This is the only module that knows about both retrieval and the LLM.
The flow:
  1. Embed the request and retrieve top-k similar past incidents
  2. Build a prompt with the retrieved incidents as grounded context
  3. Call the LLM with structured-output constraint to TriageResponse
  4. Return the validated TriageResponse
"""

from app.schemas import IncidentRequest, TriageResponse
from app.vector_store import retrieve_similar
from app.llm import call_triage_llm
from app.prompts import SYSTEM_PROMPT, build_user_prompt

TOP_K = 3  # how many similar incidents to retrieve as context


def run(request: IncidentRequest) -> TriageResponse:
    """Run the full triage RAG flow for a single request."""
    # 1. Retrieve. The query text is just the description — system and
    #    reporter are metadata, not signal for similarity. (Could be added
    #    to the query later if it improves results — eval-driven decision.)
    retrieved = retrieve_similar(request.description, k=TOP_K)

    # 2. Build prompt with retrieved context.
    user_prompt = build_user_prompt(
        new_incident_description=request.description,
        retrieved=retrieved,
    )

    # 3. Call the LLM with structured-output constraint.
    response = call_triage_llm(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    return response