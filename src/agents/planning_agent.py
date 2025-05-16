import copy
import json

from agents.base_agent import BaseAgent
from core.state import MainState
from utils.util_types import SolutionPlan
from utils.utils import extract_json_from_markdown
from utils.utils import extract_markdown_from_response


class PlanningAgent(BaseAgent):

    def _get_confidence_score(self, plan: str) -> float:

        # Copy the information for the prompt
        assert self.prompts_input, (
            'No prompts_input on self '
            'do not run method on itself without process'
        )
        prompt_inp = self.prompts_input.copy()

        # Example solutions are not needed for conf. score
        if 'example_solutions' in prompt_inp:
            prompt_inp.pop('example_solutions')
        prompt_inp['plan'] = plan

        # Create the json string
        json_inp = json.dumps(prompt_inp, indent=2)

        # Create the prompt to get the confidence for the plan
        prompt = self._get_prompt('planning_confidence', json_input=json_inp)
        self.logger.debug(f'Confidence prompt: {prompt}')

        # Prompt the model and handle the response
        ret = self.model.prompt(prompt)
        if not ret:
            self.logger.warning('No return from model, return default 0.0')
            return 0.0

        self.logger.debug(f'Confidence return: {ret}')
        json_resp = extract_json_from_markdown(ret)
        if not len(json_resp) > 0:
            self.logger.warning('Did not receive json back from model')
            return 0.0

        try:
            confidence_score = json.loads(json_resp[0])
        except json.JSONDecodeError as e:
            self.logger.warning(f'Could not decode json, {e}')
            return 0.0

        return float(confidence_score.get('confidence', 0.0))

    def _generate_solution_plan(
        self,
        prompt: str,
    ) -> SolutionPlan:
        """
        Generates the solution plan with the given prompt
        and gets the confidence score.
        """

        self.logger.debug(f'Planning Agent prompt: {prompt}')

        ret = self.model.prompt(prompt)
        self.logger.debug(f'Model response: {ret}')

        # Check if the response is empty
        if not ret:
            # TODO: Perhaps retry here?
            self.logger.warning('Planning agent response is empty')
            return SolutionPlan('', 0)

        generated_plan = extract_markdown_from_response(ret)
        if not generated_plan:
            self.logger.warning(
                'Could not extract markdown plan from response.'
                f'{generated_plan=}',
            )
            # If the response is not empty, assume the full body is the
            # markdown plan
            generated_plan = [ret]

        conf_score = self._get_confidence_score(generated_plan[0])

        return SolutionPlan(generated_plan[0], conf_score)

    def process(self, state: MainState) -> MainState:

        # Deepcopy is needed because the state is passed by reference
        state = copy.deepcopy(state)

        # Create the input for the prompts
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

        # Save to state for better acess
        self.prompts_input = inp
        json_input = json.dumps(inp, indent=2)

        self.logger.trace(f'Planning Agent: {json_input=}')

        step_by_step_prompt = self._get_prompt(
            'planning_step_by_step',
            json_input=json_input,
        )

        plans: list[SolutionPlan] = []
        highest_plan = None
        highest_score = 0

        n_plans = self.settings.get('n_plans', 3)
        self.logger.info(f'Generating {n_plans} plans')

        for i in range(n_plans):
            self.logger.info(f'Creating plan {i+1}/{n_plans}')
            plan = self._generate_solution_plan(step_by_step_prompt)
            if plan.confidence >= highest_score:
                highest_score = plan.confidence
                highest_plan = plan
            plans.append(plan)

        state.selected_plan = highest_plan
        state.generated_plans = plans

        return state
