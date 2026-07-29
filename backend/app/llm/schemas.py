from typing import Literal

from pydantic import BaseModel, field_validator

ChartType = Literal["bar", "line", "pie", "single_value"]


class QueryPlan(BaseModel):
    """Stage 1 output: what the user asked for, turned into a single SQL query."""

    intent: str
    sql: str
    params: list = []
    chart_type: ChartType
    needs_retrieval: bool = False

    @field_validator("sql")
    @classmethod
    def must_look_like_a_select(cls, value: str) -> str:
        first_word = value.strip().split(None, 1)[0].lower() if value.strip() else ""
        if first_word not in ("select", "with"):
            raise ValueError("sql must be a SELECT (or WITH ... SELECT) statement")
        return value


class AnswerPlan(BaseModel):
    """Stage 2 output: the query result turned into a grounded answer.

    recommendation is required - every question gets one, whether it's a
    playbook match or a recommendation the model composes itself grounded in
    the rows it was given (see answer_gen.py's system prompt).
    """

    answer_text: str
    recommendation: str
    cited_values: list = []

    @field_validator("recommendation")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("recommendation must not be blank - every answer needs one")
        return value
