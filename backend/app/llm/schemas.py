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
    """Stage 2 output: the query result turned into a grounded answer."""

    answer_text: str
    recommendation: str | None = None
    cited_values: list = []
