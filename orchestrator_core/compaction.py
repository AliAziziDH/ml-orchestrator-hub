from pydantic import BaseModel, Field


class CompactionSummary(BaseModel):
    active_goal: str = Field(..., description="The current overarching goal of the agent.")
    key_decisions: list[str] = Field(default_factory=list, description="Key decisions made so far.")
    files_modified: list[str] = Field(default_factory=list, description="List of files modified.")
    errors_encountered: list[str] = Field(
        default_factory=list, description="List of errors encountered."
    )
    critical_math_context: str = Field(
        ...,
        description="Crucial for retaining Kaggle Cross-Validation scores and SLSQP matrix dimensions.",
    )
