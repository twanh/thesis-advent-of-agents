import os

from agents.base_agent import BaseAgent
from agents.base_agent import MockAgent
from agents.pre_processing_agent import PreProcessingAgent
from core.orchestrator import Orchestrator
from core.state import MainState
from dotenv import load_dotenv
from models.gemini_model import GeminiLanguageModel
from utils.util_types import AgentSettings
from utils.util_types import Puzzle

if __name__ == '__main__':

    load_dotenv()

    model = GeminiLanguageModel(
        api_key=os.getenv('GEMINI_API_KEY') or '',
        model_name='gemini-2.0-flash',
    )

    # TODO: Is this the best DS to do this?
    agents: tuple[tuple[BaseAgent, AgentSettings], ...] = (
        (
            PreProcessingAgent('preprocess', model=model),
            AgentSettings(enabled=True, can_debug=False),
        ),
        (
            MockAgent('retreival', model=model),
            AgentSettings(enabled=True, can_debug=False),
        ),
        (
            MockAgent('planning', model=model),
            AgentSettings(enabled=True, can_debug=False),
        ),
        (
            MockAgent('coding', model=model),
            AgentSettings(enabled=True, can_debug=False),
        ),
        (
            MockAgent('debugging', model=model),
            AgentSettings(enabled=True, can_debug=True),
        ),
    )

    orchestrator = Orchestrator(agents, {})

    # Load a sample puzzle
    # TODO: Move to commandline argument
    with open('puzzle.txt', 'r') as f:
        puzzle_data = f.read()

    puzzle = Puzzle(
        description=puzzle_data,
        solution=None,
        year=2021,
        day=1,
    )

    state = MainState(puzzle=puzzle)

    orchestrator.solve_puzzle(state)
