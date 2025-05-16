import copy
import json

from agents.base_agent import BaseAgent
from core.state import MainState
from utils.utils import extract_json_from_markdown


class CodingAgent(BaseAgent):

    def process(self, state: MainState) -> MainState:

        # Copy the state (passed by reference)
        state = copy.deepcopy(state)

        # Create the prompt
        inp = {
            'problem_statement': state.problem_statement,
            'full_description': state.puzzle.description,
            'underlying_concepts': state.underlying_concepts,
            'keywords': state.keywords,
            'input_format': state.input_format,
            'output_format': state.output_format,
            'constraints': state.constraints,
            'example_solutions': [
                {'plan': i[1], 'code': i[0].solution}
                for i in state.retreived_puzzles
            ],
            'test_cases': state.test_cases,
            'suggestions': ' '.join(state.debug_suggestions),
        }

        if state.selected_plan is None:
            self.logger.warning(
                'Coding Agent: No plan is selected. '
                'Continuing without plan',
            )
            inp['plan'] = 'No plan for this puzzle. Solve it without.'
        else:
            inp['plan'] = state.selected_plan.plan

        json_input = json.dumps(inp, indent=2)
        self.logger.debug(f'Coding Agent: {json_input}')
        prompt = self._get_prompt('coding', json_input=json_input)

        # Prompt the model
        resp = self.model.prompt(prompt)

        if not resp:
            self.logger.warning(
                'Coding Agent: Got no response from the model.',
            )
            # TODO Implement retry
            return state

        # Try to extract the json from the response
        json_resp = extract_json_from_markdown(resp)
        if not json_resp:
            self.logger.debug(f'Got {json_resp=} for {resp=}')
            self.logger.warning(
                f'Coding Agent: Could not extract json from response {resp=}',
            )
            state = self._invalid_response_retry(state)

        try:
            obj = json.loads(json_resp[0])
            # NOTE: Is this the correct way to indicate no code is found?
            state.generated_code = obj.get('code')
            if state.generated_code is None:
                self.logger.warning('No code was found in resp json')
                return self._invalid_response_retry(state)

        except json.JSONDecodeError as e:
            self.logger.warning(f'Could not decode JSON, {e=}')
            state = self._invalid_response_retry(state)

        return state
