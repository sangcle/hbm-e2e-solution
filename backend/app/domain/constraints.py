from pydantic import BaseModel, Field


class ConstraintResult(BaseModel):
    is_feasible: bool = True
    violated_constraints: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    margins: dict[str, float] = Field(default_factory=dict)
    severity: dict[str, float] = Field(default_factory=dict)
    policy_results: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
