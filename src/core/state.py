from dataclasses import dataclass
from dataclasses import field
from typing import Any

from utils.util_types import Puzzle
from utils.util_types import SolutionPlan
from utils.util_types import TestCase


@dataclass
class MainState:
    """
    The main state of the system.

    The state is passed through all the agents and updated as necessary.
    The final result will be the solution code.

    Note: the state is still subject to change as the system is developed.
    """

    # Inital input
    puzzle: Puzzle

    # Preprocessing output
    problem_statement: str | None = None
    input_format: str | None = None
    output_format: str | None = None
    # TODO: Create test case type
    test_cases: list[TestCase] = field(default_factory=list)
    constraints: list[str] | None = None
    keywords: list[str] = field(default_factory=list)
    underlying_concepts: list[str] = field(default_factory=list)

    # Retreival output
    # list of tuples containing the puzzle and the plan on how to is_solved
    # the puzzle
    retreived_puzzles: list[tuple[Puzzle, str]] = field(
        default_factory=list,
    )

    # Planning output
    selected_plan: SolutionPlan | None = None
    # List of plans and their confidence scores (plan, confidence)
    generated_plans: list[SolutionPlan] = field(default_factory=list)

    # Coding output
    generated_code: str | None = None

    # Debugging output
    final_code: str | None = None
    debug_attempts: int = 0
    debug_errors: list[str] = field(default_factory=list)
    is_solved: bool = False

    # General metadata
    # TODO: Add more metadata/see what is nessesary?
    agent_log: list[dict[str, Any]] = field(
        default_factory=list,
    )  # List of agent logs
    agent_errors: list[dict[str, Any]] = field(default_factory=list)
    current_step: str | None = None
