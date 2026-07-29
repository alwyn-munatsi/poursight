"""Stage 2: turn a query result into a grounded natural-language answer.

Forced tool_choice again, so the response is always the AnswerPlan shape.
Every answer gets a recommendation: the model prefers a playbook candidate
when one was matched, and otherwise composes its own - grounded in the rows
it was given, not invented advice. recommendation is never null.
"""

import json

from openai import OpenAI

from app import config
from app.llm.client import get_client
from app.llm.schemas import AnswerPlan
from app.playbook.rules import PlaybookMatch

TOOL_NAME = "emit_answer"

TOOL = {
    "type": "function",
    "function": {
        "name": TOOL_NAME,
        "description": (
            "Write a grounded natural-language answer for the manager, citing only values present "
            "in the query result."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "answer_text": {
                    "type": "string",
                    "description": "2-4 sentence plain-English answer to the question.",
                },
                "recommendation": {
                    "type": "string",
                    "description": (
                        "A short, specific, actionable recommendation - never blank. Prefer one of "
                        "the candidate recommendations (lightly reworded is fine) when one is given "
                        "and fits. Otherwise, compose your own recommendation grounded directly in "
                        "the rows you were given."
                    ),
                },
                "cited_values": {
                    "type": "array",
                    "items": {},
                    "description": (
                        "Every number or short string from the query result that answer_text states "
                        "as fact, listed exactly as it appears in the result rows."
                    ),
                },
            },
            "required": ["answer_text", "recommendation", "cited_values"],
        },
    },
}


def build_system_prompt() -> str:
    return (
        "You are PourSight's answer writer for The Arsenal Bar & Grill. You are given the exact "
        "rows a SQL query returned and must describe them accurately in plain English for a busy "
        "manager - never invent a fact that isn't in the rows.\n\n"
        "Rules:\n"
        "- Every number or name you state in answer_text as fact (item names, categories, amounts, "
        "counts, percentages) must come directly from the provided rows.\n"
        "- List every such fact in cited_values, exactly as given (same type, same spelling/precision) "
        "- this includes item/category names, not just numbers.\n"
        "- Every answer needs a recommendation - it is never blank. If a candidate recommendation is "
        "provided and genuinely fits, use it (light rewording to flow with your answer is fine, but "
        "don't change its meaning). If no candidate is provided, or none fit, write your own short, "
        "specific, actionable recommendation yourself, directly tied to the numbers in these rows - "
        "e.g. what to watch, restock, price, or staff for, given what this result actually shows. "
        "Never write a generic recommendation that ignores the data, and never invent a new number or "
        "fact to justify it that wasn't already in the rows or in answer_text.\n"
        "- Keep answer_text to 2-4 sentences, and the recommendation to one sentence."
    )


def _user_content(
    intent: str,
    rows: list[dict],
    playbook_matches: list[PlaybookMatch],
    retrieved_context: str | None,
) -> str:
    parts = [
        f"Question intent: {intent}",
        f"Query result rows (JSON): {json.dumps(rows, default=str)}",
    ]
    if playbook_matches:
        candidates = "\n".join(f"- ({m.rule_id}) {m.recommendation}" for m in playbook_matches)
        parts.append(f"Candidate recommendations:\n{candidates}")
    else:
        parts.append("Candidate recommendations: none.")
    if retrieved_context:
        parts.append(f"Relevant menu/recipe context:\n{retrieved_context}")
    return "\n\n".join(parts)


def generate_answer(
    intent: str,
    rows: list[dict],
    playbook_matches: list[PlaybookMatch] | None = None,
    retrieved_context: str | None = None,
    client: OpenAI | None = None,
) -> AnswerPlan:
    client = client or get_client()
    playbook_matches = playbook_matches or []

    response = client.chat.completions.create(
        model=config.GROQ_MODEL,
        max_tokens=1024,
        messages=[
            {"role": "system", "content": build_system_prompt()},
            {"role": "user", "content": _user_content(intent, rows, playbook_matches, retrieved_context)},
        ],
        tools=[TOOL],
        tool_choice={"type": "function", "function": {"name": TOOL_NAME}},
    )

    message = response.choices[0].message
    tool_calls = message.tool_calls or []
    for call in tool_calls:
        if call.function.name == TOOL_NAME:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Model returned invalid JSON for {TOOL_NAME}: {exc}") from exc
            return AnswerPlan.model_validate(arguments)

    raise RuntimeError(f"Model did not call {TOOL_NAME}: {message.content!r}")
