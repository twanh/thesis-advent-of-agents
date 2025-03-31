from dataclasses import dataclass
from dataclasses import field
from typing import Any


@dataclass
class MainState:
    """
    The main state of the system.

    The state is passed through all the agents and updated as necessary.
    The final result will be the solution code.

    Note: the state is still subject to change as the system is developed.
    """

    # Inital input
    puzzle_year: int
    puzzle_day: int
    puzzle_part: int
    raw_puzzle_description: str

    # Preprocessing output
    problem_statement: str | None = None
    input_format: str | None = None
    test_input: str | None = None
    test_expected_output: str | None = None
    keywords: list[str] = field(default_factory=list)
    underlying_concepts: list[str] = field(default_factory=list)

    # Retreival output
    retreived_puzzles: list[dict[str, str]] = field(
        default_factory=list,
    )  # List of puzzles (description, solution)

    # Planning output
    selected_plan: str | None = None
    confidence_score: float | None = None
    # List of plans and their confidence scores (plan, confidence)
    generated_plans: list[tuple[str, float]] = field(default_factory=list)

    # Coding output
    generated_code: str | None = None

    # Debugging output
    final_code: str | None = None
    debug_attempts: int = 0
    debug_errors: list[str] = field(default_factory=list)
    is_solved: bool = False

    # General metadata
    agent_log: list[dict[str, Any]] = field(
        default_factory=list,
    )  # List of agent logs
    agent_errors: list[dict[str, Any]] = field(default_factory=list)
    current_step: str | None = None
