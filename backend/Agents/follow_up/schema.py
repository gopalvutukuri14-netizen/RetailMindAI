from enum import Enum
from pydantic import BaseModel, Field


class SuggestionType(str, Enum):
    COMPARE = "compare"
    REFINE_FILTER = "refine_filter"
    BROADEN_SEARCH = "broaden_search"
    CLARIFY = "clarify"


class FollowUpSuggestion(BaseModel):
    suggestion_text: str = Field(
        description="The actual question/action to show the user, phrased naturally, "
                     "e.g. 'Want me to compare the top 2 options?'"
    )
    suggestion_type: SuggestionType


class FollowUpResult(BaseModel):
    suggestions: list[FollowUpSuggestion] = Field(default_factory=list)