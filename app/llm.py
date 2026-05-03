"""
LLM wrapper — OpenAI chat completion with structured output.

Single responsibility: take a system prompt and a user prompt, return
a TriageResponse instance. Uses OpenAI's structured output mode with
the Pydantic schema as the source of truth — the same TriageResponse
that defines our API contract also constrains the LLM's response.
That's the schema-as-source-of-truth pattern: no schema drift between
the API and the LLM.

Day 21: this module is called by app/triage.py.
"""

from typing import Optional
from openai import OpenAI, OpenAIError
from app.schemas import TriageResponse

LLM_MODEL = "gpt-4o-mini"  # cheapest tier with native structured output support
_openai_client: Optional[OpenAI] = None


def _get_openai() -> OpenAI:
    """Lazy init the OpenAI client. Same pattern as vector_store.py."""
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI()
    return _openai_client


class LLMError(Exception):
    """Raised when the LLM call fails or returns unparseable output."""


def call_triage_llm(system_prompt: str, user_prompt: str) -> TriageResponse:
    """
    Call the LLM with structured output constrained to TriageResponse.

    Returns a validated TriageResponse instance. Raises LLMError on
    transient failures, refusals, or schema validation failures.

    The OpenAI SDK retries transient failures (5xx, network errors)
    automatically — default is 2 retries with exponential backoff.
    We don't add our own retry layer on top.
    """
    try:
        completion = _get_openai().beta.chat.completions.parse(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format=TriageResponse,  # Pydantic model = JSON schema constraint
            temperature=0.2,                  # low but not zero — slight variety in phrasing
        )
    except OpenAIError as e:
        raise LLMError(f"OpenAI API call failed: {e}") from e

    message = completion.choices[0].message

    # Structured-output mode can return a "refusal" if the model declines
    # the request (safety reasons). We treat that as a hard failure.
    if message.refusal:
        raise LLMError(f"Model refused to respond: {message.refusal}")

    # message.parsed is the typed TriageResponse instance (or None if parsing
    # failed — shouldn't happen with structured output, but defensive check).
    if message.parsed is None:
        raise LLMError("Model returned no parseable response")

    return message.parsed