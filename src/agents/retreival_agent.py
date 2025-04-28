import json
from copy import deepcopy

from agents.base_agent import BaseAgent
from core.retreival import PuzzleRetreival
from core.state import MainState
from models.base_model import BaseLanguageModel
from utils.util_types import Puzzle
from utils.utils import extract_json_from_markdown


class RetrievalAgent(BaseAgent):

    def __init__(
            self,
            agent_name: str,
            model: BaseLanguageModel,
            **settings: str,
    ):

        super().__init__(agent_name, model, **settings)

        # Check that required settings are given
        con_string = self.settings.get('connection_string', None)
        openai_key = self.settings.get('openai_key', None)

        if con_string is None:
            self.logger.error(
                'connection_string is required kwarg for RetreivalAgent ',
            )
            raise ValueError('Expected connection_string argument')

        if openai_key is None:
            self.logger.error(
                'openai_key is required kwarg (setting) for RetreivalAgent ',
            )
            raise ValueError('Expected openai_key argument')

        self.puzzle_retreival = PuzzleRetreival(
            connection_string=con_string,
            openai_key=openai_key,
        )

        self.puzzle_retreival.init_db()

    def process(self, state: MainState) -> MainState:

        state = deepcopy(state)

        # Retreive all similar puzzles
        # TODO: Use the limit (get this from settings)
        puzzles = self.puzzle_retreival.get_similar_puzzles_from_state(state)

        self.logger.debug(f'Found {len(puzzles)} similar puzzles')

        puzzles_with_solutions: list[Puzzle] = []

        # TODO: Should we error when no similar puzzles are found?
        for puzzle in puzzles:
            puzzle_solutions = self.puzzle_retreival.get_solutions(
                puzzle.year,
                puzzle.day,
                # TODO: implement limit
            )

            self.logger.debug(
                f'Found {len(puzzle_solutions)} solutions for puzzle',
            )
            self.logger.trace(f'{puzzle=}')

            if len(puzzle_solutions) < 1:
                self.logger.warning(
                    'Did not find any solutions for puzzle. Skipping...',
                )
                continue

            inp = {
                'problem_statement': puzzle.problem_statement,
                'full_description': puzzle.full_description,
                'underlying_concepts': puzzle.underlying_concepts,
                'keywords': puzzle.keywords,
                'solutions': [
                    {
                        'solution_id': f'solution-{i}',
                        'code': sol.code,
                    } for i, sol in enumerate(puzzle_solutions)
                ],
            }

            prompt = self._get_prompt(
                'retreival_rank_solutions',
                json_input=json.dumps(inp),
            )

            self.logger.debug(f'Retreival agent prompt: {prompt}')

            ret = self.model.prompt(prompt)
            self.logger.debug(f'Model response: {ret}')

            if not ret:
                self.logger.warning('RetreivalAgent response is empty')
                continue

            # Extract json
            extracted = extract_json_from_markdown(ret)
            data = json.loads(extracted[0])
            self.logger.trace(f'Extracted {extracted} json from response')

            # Get the top ranked solution for the current puzzle
            ranked_sols = data.get('ranked_solutions', [])
            top_rank_id = list(
                filter(lambda x: x['rank'] == 1, ranked_sols),
            )[0].get('solution_id', '')

            top_solution_code = list(
                filter(
                    lambda x: x['solution_id'] ==
                    top_rank_id, inp['solutions'],
                ),
            )[0]

            self.logger.debug(
                (
                    'Top ranked solution for puzzle '
                    f'{puzzle.day}-{puzzle.year} is '
                    f'{top_solution_code}'
                ),
            )

            puzzles_with_solutions.append(
                Puzzle(
                    description=puzzle.full_description,
                    solution=top_solution_code,
                    year=puzzle.year,
                    day=puzzle.day,
                ),
            )

        state.retreived_puzzles = puzzles_with_solutions

        return state
