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
            **settings: str | None | dict[str, float],
    ):

        super().__init__(agent_name, model, **settings)

        # Get the retreival limit (# of puzzles/solutions to retreive)
        # default to 3
        self.retreival_limit = self.settings.get('limit', 3)
        self.retries = 0

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
            weights=self.settings.get('weights', None),
        )

        self.puzzle_retreival.init_db()

    def process(self, state: MainState) -> MainState:

        # dataclass is passed by reference
        # so we need to deepcopy it in order to not modify the original
        state = deepcopy(state)

        # Retreive all similar puzzles
        puzzles = self.puzzle_retreival.get_similar_puzzles_from_state(
            state,
            limit=self.retreival_limit,
        )

        self.logger.debug(f'Found {len(puzzles)} similar puzzles')

        puzzles_with_solutions: list[tuple[Puzzle, str]] = []

        # TODO: Should we error when no similar puzzles are found?
        for puzzle in puzzles:
            puzzle_solutions = self.puzzle_retreival.get_solutions(
                puzzle.year,
                puzzle.day,
                limit=self.retreival_limit,
            )

            self.logger.debug(
                f'Found {len(puzzle_solutions)} solutions for puzzle',
            )
            self.logger.trace(f'{puzzle=}')

            if len(puzzle_solutions) < 1:
                self.logger.warning(
                    'Did not find any solutions for puzzle'
                    f'{puzzle.day}-{puzzle.year}. Skipping...',
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
                # TODO: Handle this case, raise error or make
                # sure that the other agents can handle this
                self.logger.warning('RetreivalAgent response is empty')
                continue

            # Extract json
            extracted = extract_json_from_markdown(ret)
            try:
                data = json.loads(extracted[0])
                self.logger.trace(f'Extracted {extracted} json from response')
            except json.JSONDecodeError as e:
                self.logger.warning('Could not decode json: ', e)
                # TODO: Do not hardcode n retries
                if self.retries < 3:
                    self.logger.info(
                        f'Retrying retreival agent {self.retries}/3',
                    )
                    self.retries += 1
                    return self.process(state)
                else:
                    self.logger.error(
                        'Could not decode json after 3 retries',
                    )
                    raise ValueError('Could not decode json', e)

            # Get the top ranked solution for the current puzzle
            ranked_sols = data.get('ranked_solutions', [])

            top_ranked_solution = next(
                (sol for sol in ranked_sols if sol.get('rank', 0) == 1),
                None,
            )

            if top_ranked_solution is None:
                self.logger.error(
                    'Could not find a top ranked solution: ', ranked_sols,
                )
                raise ValueError('No rank=1 found')

            top_rank_id = top_ranked_solution.get('solution_id', '')
            top_rank_plan = top_ranked_solution.get('plan', '')

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
                    f'{top_solution_code} with plan {top_rank_plan}'
                ),
            )

            puzzles_with_solutions.append(
                (
                    Puzzle(
                        description=puzzle.full_description,
                        solution=top_solution_code,
                        year=puzzle.year,
                        day=puzzle.day,
                    ),
                    top_rank_plan,
                ),
            )

        state.retreived_puzzles = puzzles_with_solutions

        return state
