"""
Pydantic schemas — the API contract.

Every request body and response body for the /triage endpoint goes
through one of these models. FastAPI uses them for:
  - validating incoming JSON (returns 422 automatically if wrong)
  - serializing outgoing responses
  - generating the OpenAPI / Swagger docs at /docs
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


# ---------- Request ----------

class IncidentRequest(BaseModel):
    """What a client sends to POST /triage."""

    description: str = Field(
        ...,
        min_length=10,
        description="Free-text description of the incident. Required.",
        examples=["Checkout API returning 502s for ~5% of requests since 14:20 UTC."],
    )
    reporter: Optional[str] = Field(
        default=None,
        description="Who flagged the incident. Optional, useful for audit.",
        examples=["alice@company.com"],
    )
    system: Optional[str] = Field(
        default=None,
        description="System the incident is on, if known.",
        examples=["checkout-service"],
    )


# ---------- Response ----------

# Constrained string sets. Using Literal (not free-form str) means:
#   1. Downstream consumers (PagerDuty, dashboards) get predictable values.
#   2. On Day 21 we'll constrain the LLM's output to these same enums via
#      OpenAI's structured-output mode. Locking them now = Day 21 is just plumbing.

Severity = Literal["P1", "P2", "P3", "P4"]
Category = Literal[
    "outage",
    "security",
    "performance",
    "data_integrity",
    "deployment_failure",
]


class TriageResponse(BaseModel):
    """What the API returns from POST /triage."""

    severity: Severity = Field(
        ...,
        description="Suggested severity. P1 = critical, P4 = low.",
    )
    category: Category = Field(
        ...,
        description="Suggested incident category.",
    )
    recommended_action: str = Field(
        ...,
        description="One-line first-response suggestion for the on-call.",
    )
    reasoning: str = Field(
        ...,
        description="Why the model picked this severity/category. Surfaces the "
                    "RAG output's grounding so an on-call can verify before acting.",
    )
    similar_incidents: list[str] = Field(
        default_factory=list,
        description="IDs of past incidents retrieved from the vector store that "
                    "informed this triage. Empty until Day 20.",
    )
