import copy
import os
import subprocess
import tempfile

from agents.base_agent import BaseAgent
from core.state import MainState


class DebuggingAgent(BaseAgent):

    def _run_code(
        self,
        code: str,
        input_: str,
    ) -> tuple[str | None, str | None]:

        # Create tempfile for the code
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as cf:
            # Write the code
            cf.write(code.encode('utf-8'))
            # Save the path to be exectued later
            code_file_path = cf.name
            self.logger.debug(f'Saved code to {code_file_path}')

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as inpf:
            # Write the test input file
            inpf.write(input_.encode('utf-8'))
            input_file_path = inpf.name
            self.logger.debug(f'Saved input to {input_file_path}')

        try:
            self.logger.info('Running code')
            self.logger.debug(f'Running: {code=} {input_=}')
            # RUn the code
            process = subprocess.run(
                ['python3', code_file_path, input_file_path],
                text=True,
                capture_output=True,
                timeout=5,  # Prevent loops etc (TODO: Find good timeout)
            )
            output = process.stdout.strip()
            stderr = process.stderr.strip()
            self.logger.debug(f'Got output: {output}')
            self.logger.debug(f'Got stderr: {stderr}')
            return output, stderr
        except subprocess.TimeoutExpired:
            # Handle timeout
            self.logger.warning('Timeout for running code expired.')
            return None, None
        except Exception as e:
            self.logger.warning(f'Could not execute code: {e}')
            return None, None
        finally:
            # Cleanup
            os.remove(code_file_path)
            os.remove(input_file_path)

    def _analyze_errors(self, code: str, errors: str) -> None:

        # TODO: Implement
        self.logger.info('Debug Agent: Analyzing errors')
        return None

    def _cycle_plans(self, state: MainState) -> MainState:

        # Move to the next plan in generated_plans (making sure not the
        # current plan is selected)
        if state.generated_plans is None or len(state.generated_plans) == 0:
            self.logger.error('No generated plans to cycle through.')
            return state

        # TODO: Should we sort on confidence?
        next_plan = state.generated_plans.pop(0)
        state.selected_plan = next_plan
        return state

    def process(self, state: MainState) -> MainState:

        state = copy.deepcopy(state)

        # Check that all the requirements to run a valid
        puzzle_input = self.settings.get('puzzle_input')
        if not puzzle_input:
            self.logger.error('Debugger requires puzzle input to run.')
            raise ValueError('No puzze_input in settings')
        if state.generated_code is None:
            self.logger.error('Debugger requires code to run.')
            return state

        # If we know the expected output for the puzzle
        # then immidiatly try if it works
        expected_output = self.settings.get('expected_output', None)
        if expected_output is not None:
            self.logger.info('Debug Agent: Running code with test input')
            actual_output, errors = self._run_code(
                state.generated_code, puzzle_input,
            )
            self.logger.info(
                f'Expected: {expected_output} got {actual_output}',
            )
            if actual_output == expected_output:
                self.logger.success('Got expected output, puzzle is solved.')
                # The solution generates the correct output
                # the puzzle is solved!
                state.final_code = state.generated_code
                state.is_solved = True
                return state

            # If the output was None and the errors are None the subprocess
            # raised and there is not a lot of information to debug
            # this means we switch plans
            if actual_output is None and errors is None:
                self.logger.warning('No output from code, switching plans.')
                return self._cycle_plans(state)

            if errors is not None:
                self._analyze_errors(state.generated_code, errors)

        # Check the result on the test cases

        # If there are (syntax) errors:
        # Backtrack: to coding agent

        # Result on test cases:
        # fail -> backtrack planning / coding agent
        # sucess: continue

        # Check the result on the final expected output

        return state
