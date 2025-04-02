from typing import NamedTuple


class Puzzle(NamedTuple):
    """
    A puzzle tuple that contains the description and solution.
    """

    description: str
    solution: str | None
    year: int
    day: int


class SolutionPlan(NamedTuple):
    """
    A solution plan tuple that contains the plan and confidence score.
    """

    plan: str
    confidence: float


class AgentSettings(NamedTuple):

    enabled: bool
    can_debug: bool
