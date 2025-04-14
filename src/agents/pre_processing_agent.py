import copy
import json

from agents.base_agent import BaseAgent
from core.state import MainState
from utils.utils import extract_json_from_markdown


class PreProcessingAgent(BaseAgent):

    def process(self, state: MainState) -> MainState:

        # Deepcopy is needed because the state is passed by reference
        state = copy.deepcopy(state)

        prompt = self._get_prompt(
            'pre_processing',
            puzzle=state.puzzle.description,
        )

        self.logger.debug(f'Preprocessing agent prompt: {prompt}')
        ret = self.model.prompt(prompt)
        self.logger.debug(f'Model response: {ret}')

        # Check if the response is empty
        if not ret:
            self.logger.warning('Preprocessing agent response is empty')
            return state

        # Get the json from the markdown response
        extracted_json = extract_json_from_markdown(ret)
        self.logger.trace(f'Extracted {extracted_json} from response')

        # Parse the response
        try:
            response: dict = json.loads(extracted_json[0])

            # Update all required fields on the state
            required_fields = (
                'problem_statement', 'input_format',
                'output_format', 'constraints', 'keywords',
                'underlying_concepts',
            )

            for required_field in required_fields:
                value = response.get(required_field, None)
                if value is not None:
                    setattr(state, required_field, value)
                else:
                    self.logger.warning(
                        f'Missing required_field: `{required_field}`',
                    )

            test_cases: list[dict[str, str]] | None = response.get(
                'test_cases', None,
            )

            if test_cases is not None:
                for test_case in test_cases:
                    if isinstance(test_case, dict):
                        inp = test_case.get('input')
                        out = test_case.get('output')
                        if inp is not None and out is not None:
                            state.test_cases.append((inp, out))
                        else:
                            self.logger.warning(
                                'Missing input/output for test case: '
                                f' {test_case}',
                            )
            else:
                state.test_cases = []
                self.logger.warning('Missing field `test_cases`')

        except json.JSONDecodeError as e:
            self.logger.error(f'Error parsing JSON: {e}')

        return state
