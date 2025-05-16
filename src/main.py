import argparse
import os
import sys

from agents.base_agent import BaseAgent
from agents.coding_agent import CodingAgent
from agents.debugging_agent import DebuggingAgent
from agents.planning_agent import PlanningAgent
from agents.pre_processing_agent import PreProcessingAgent
from agents.retreival_agent import RetrievalAgent
from core.orchestrator import Orchestrator
from core.state import MainState
from dotenv import load_dotenv
from loguru import logger
from models.base_model import BaseLanguageModel
from models.deepseek_model import DeepseekLanguageModel
from models.gemini_model import GeminiLanguageModel
from models.openai_model import OpenAILanguageModel
from utils.util_types import AgentSettings
from utils.util_types import Puzzle
from utils.util_types import TestCase


def _parse_args() -> argparse.Namespace:

    parser = argparse.ArgumentParser(
        'Advent of Agents Advent of Code puzzle solver',
    )

    # Puzzle input arguments
    parser.add_argument(
        '--puzzle',
        type=str,
        help='The path to the file containing the puzzle (description)',
        required=True,
    )
    parser.add_argument(
        '--puzzle-input',
        type=str,
        help='The file containing the input for the puzzle',
        required=True,
    )
    parser.add_argument('--day', type=int, help='The day of the puzzle')
    parser.add_argument('--year', type=int, help='The day of the puzzle')
    parser.add_argument(
        '--expected-output',
        type=str,
        help='The expected output for the puzzle',
    )

    # Agent configuration
    parser.add_argument(
        '--disable-agents',
        type=str,
        nargs='*',
        choices=['preprocess', 'retreival', 'planning', 'coding', 'debugging'],
        help='The agents to disable',
    )

    # Model configuration
    parser.add_argument(
        '--default-model',
        type=str,
        default='gemini-2.0-flash',
        help='The default model to use for the agents',
    )

    # Individual agent model configuration
    parser.add_argument(
        '--preprocess-model',
        type=str,
        help='Model to use for the preprocessing agent',
    )
    parser.add_argument(
        '--retreival-model',
        type=str,
        help='Model to use for the retrieval agent',
    )
    parser.add_argument(
        '--planning-model',
        type=str,
        help='Model to use for the planning agent',
    )
    parser.add_argument(
        '--coding-model',
        type=str,
        help='Model to use for the coding agent',
    )
    parser.add_argument(
        '--debugging-model',
        type=str,
        help='Model to use for the debugging agent',
    )
    # Logging configuration
    parser.add_argument(
        '-l', '--log-level',
        type=str,
        default='INFO',
        choices=['TRACE', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        help='Set the logging level',
    )

    return parser.parse_args()


def _get_model(model_name: str) -> BaseLanguageModel:

    if model_name.startswith('gemini'):
        return GeminiLanguageModel(
            api_key=os.getenv('GEMINI_API_KEY') or '',
            model_name=model_name,
        )
    elif model_name.startswith('openai') or model_name.startswith('gpt'):
        return OpenAILanguageModel(
            api_key=os.getenv('OPENAI_API_KEY') or '',
            model_name=model_name,
        )
    elif model_name.startswith('deepseek'):
        return DeepseekLanguageModel(
            api_key=os.getenv('DEEPSEEK_API_KEY') or '',
            model_name=model_name,
        )

    raise ValueError(f'Unknown model name: {model_name}')


if __name__ == '__main__':

    args = _parse_args()

    load_dotenv()

    logger.remove()
    logger.add(sys.stdout, level=args.log_level)

    agents_models = {
        'preprocess': _get_model(args.preprocess_model or args.default_model),
        'retreival': _get_model(args.retreival_model or args.default_model),
        'planning': _get_model(args.planning_model or args.default_model),
        'coding': _get_model(args.coding_model or args.default_model),
        'debugging': _get_model(args.debugging_model or args.default_model),
    }

    # Quick helper lambda function to see if the agent is enabled
    if args.disable_agents is None:
        def is_enabled(_): return True
    else:
        def is_enabled(agent_name): return True if agent_name not in args.disable_agents else False  # noqa: E501

    # Load the puzzle input
    with open(args.puzzle_input, 'r') as inpf:
        puzzle_input = inpf.read()

    agents: tuple[tuple[BaseAgent, AgentSettings], ...] = (
        (
            PreProcessingAgent(
                'preprocess', model=agents_models['preprocess'],
            ),
            AgentSettings(enabled=is_enabled('preprocess'), can_debug=False),
        ),
        (
            RetrievalAgent(
                'retreival',
                model=agents_models['retreival'],
                connection_string=os.getenv('DB_CONNECTION_STRING') or '',
                openai_key=os.getenv('OPENAI_API_KEY') or '',
                # Use default weights
                weights=None,
            ),
            AgentSettings(enabled=is_enabled('retreival'), can_debug=False),
        ),
        (
            # TODO: Make n_plans commandline argument?
            PlanningAgent(
                'planning',
                model=agents_models['planning'],
                n_plans=3,
            ),
            AgentSettings(enabled=is_enabled('planning'), can_debug=False),
        ),
        (
            CodingAgent('coding', model=agents_models['coding']),
            AgentSettings(enabled=is_enabled('coding'), can_debug=False),
        ),
        (
            DebuggingAgent(
                'debugging',
                model=agents_models['debugging'],
                expected_output=args.expected_output,
                puzzle_input=puzzle_input,
            ),
            AgentSettings(enabled=is_enabled('debugging'), can_debug=True),
        ),
    )

    orchestrator = Orchestrator(agents, {})

    # Load the puzzle
    with open(args.puzzle, 'r') as f:
        puzzle_data = f.read()

    puzzle = Puzzle(
        description=puzzle_data,
        solution=None,
        year=args.year or 2024,  # set default year to 2024
        day=args.day or 1,  # set default day to 1
    )

    state = MainState(puzzle=puzzle)
    ret_state = orchestrator.solve_puzzle(state)

    # Check if the debugging agent was disabled
    # if not: test the code here
    if not is_enabled('debugging'):
        logger.info('Debugging agent was disabled, checking code')
        # Using debugging agent under the hood because
        # we otherwise have to reimplement the code running
        # but skipping all debugging steps
        dba = DebuggingAgent(
            'debugging',
            model=agents_models['debugging'],
            expected_output=args.expected_output,
            puzzle_input=puzzle_input,
        )
        run_result = dba._run_test(
            ret_state.generated_code or '',
            TestCase(
                input_=puzzle_input,
                expected_output=args.expected_output,
            ),
        )
        if run_result.success:
            logger.success('Code passed the test')
            ret_state.is_solved = True
            ret_state.final_code = ret_state.generated_code

    if ret_state.is_solved:
        logger.success(f'Puzzle {puzzle.year}-{puzzle.day} solved')
        logger.info('Final code:\n{}', ret_state.final_code)
    else:
        logger.error(f'Could not solve puzzle {puzzle.year}-{puzzle.day}')
