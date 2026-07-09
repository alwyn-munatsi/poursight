"""The one route that ties Phases 02-05 together: a question in, a grounded
answer out. See PROMPTS.md and the process-flow section of the build plan
for what each step below does and why.
"""

import logging
import sqlite3

import openai
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ValidationError

from app import config
from app.api.chart_builder import build_chart
from app.db.query_engine import QueryValidationError, run_query
from app.llm.answer_gen import generate_answer
from app.llm.nl_to_sql import plan_query
from app.playbook.rules import match_playbook
from app.retrieval.embed_docs import retrieve_context

# ValidationError/RuntimeError: the model didn't call the tool, or called it with a bad shape.
# openai.OpenAIError: any real failure talking to Groq (auth, rate limit, connection, timeout) —
# the openai SDK's base exception, used here since Groq's API is OpenAI-compatible.
LLM_ERRORS = (ValidationError, RuntimeError, openai.OpenAIError)

logger = logging.getLogger("poursight.ask")
router = APIRouter()


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    answer_text: str
    recommendation: str | None
    chart: dict | None
    cited_values: list
    intent: str
    sql: str
    row_count: int
    truncated: bool


@router.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/api/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty")
    if not config.GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GROQ_API_KEY is not configured on the server — add it to .env and restart.",
        )

    try:
        plan = plan_query(question)
    except LLM_ERRORS as exc:
        logger.warning("query planning failed for %r: %s", question, exc)
        raise HTTPException(
            status_code=422, detail=f"Could not turn that question into a query: {exc}"
        ) from exc

    try:
        result = run_query(plan.sql, tuple(plan.params))
    except (QueryValidationError, sqlite3.DatabaseError) as exc:
        logger.warning("generated SQL rejected for %r: %s | sql=%s", question, exc, plan.sql)
        raise HTTPException(status_code=422, detail=f"Generated query failed validation: {exc}") from exc

    matches = match_playbook(result.rows)
    context = retrieve_context(question) if plan.needs_retrieval else None

    try:
        answer = generate_answer(
            intent=plan.intent,
            rows=result.rows,
            playbook_matches=matches,
            retrieved_context=context,
        )
    except LLM_ERRORS as exc:
        logger.warning("answer generation failed for %r: %s", question, exc)
        raise HTTPException(status_code=422, detail=f"Could not generate an answer: {exc}") from exc

    logger.info(
        "question=%r intent=%r rows=%d truncated=%s playbook_matches=%d recommendation=%s",
        question, plan.intent, result.row_count, result.truncated, len(matches),
        bool(answer.recommendation),
    )

    return AskResponse(
        answer_text=answer.answer_text,
        recommendation=answer.recommendation,
        chart=build_chart(plan.chart_type, result.rows),
        cited_values=answer.cited_values,
        intent=plan.intent,
        sql=plan.sql,
        row_count=result.row_count,
        truncated=result.truncated,
    )
