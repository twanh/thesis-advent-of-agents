import copy
import json

from agents.base_agent import BaseAgent
from core.state import MainState
from utils.util_types import SolutionPlan
from utils.utils import extract_markdown_from_response


class PlanningAgent(BaseAgent):

    def process(self, state: MainState) -> MainState:

        # Deepcopy is needed because the state is passed by reference
        state = copy.deepcopy(state)

        example_solutions_inp = [
            {
                'puzzle': ret[0].description,
                'plan': ret[1],
                'code': ret[0].solution,
            } for ret in state.retreived_puzzles
        ]

        inp = {
            'problem_statement': state.problem_statement,
            'full_description': state.puzzle.description,
            'underlying_concepts': state.underlying_concepts,
            'keywords': state.keywords,
            'constraints': state.constraints,
            'example_solutions': example_solutions_inp,
        }

        json_input = json.dumps(inp, indent=2)

        self.logger.trace(f'Planning Agent: {json_input=}')

        step_by_step_prompt = self._get_prompt(
            'planning_step_by_step',
            json_input=json_input,
        )

        self.logger.debug(f'Planning Agent prompt: {step_by_step_prompt}')
        ret = self.model.prompt(step_by_step_prompt)
        self.logger.debug(f'Model response: {ret}')

        # Check if the response is empty
        if not ret:
            # TODO: Perhaps retry here?
            self.logger.warning('Planning agent response is empty')
            return state

        generated_plan = extract_markdown_from_response(ret)[0]

        state.selected_plan = SolutionPlan(generated_plan, 1)

        return state
