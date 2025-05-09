import copy
import json
import os
import subprocess
import tempfile
from typing import Literal
from typing import NamedTuple

from agents.base_agent import BaseAgent
from core.state import MainState
from models.base_model import BaseLanguageModel
from utils.util_types import TestCase
from utils.utils import extract_json_from_markdown

MAX_CODE_FIXES = 2


class DebugAnalysisResult(NamedTuple):
    decision: Literal['fix_myself', 'delegate', 'no_fix']
    fixed_code: str | None
    suggestions: str | None


class TestCaseResult(NamedTuple):
    success: bool
    expected_output: str | None
    actual_output: str | None
    errors: str | None


class DebuggingAgent(BaseAgent):

    def __init__(
            self,
            agent_name: str,
            model: BaseLanguageModel,
            **settings: str,
    ):
        super().__init__(agent_name, model, **settings)

        self.code_fixes = 0
        self.delegations = 0

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
            # Will return None if stderr is empty string
            return output, stderr or None
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

    def _run_test_case(self, code: str, test_case: TestCase) -> TestCaseResult:

        # Run the code with the test case
        self.logger.info('Running code with test case')
        output, errors = self._run_code(code, test_case.input_)
        self.logger.debug(
            f'Test results: {output=} {errors=} '
            f'was expecting: {test_case.expected_output}',
        )

        if output == test_case.expected_output:
            self.logger.info('Test case is successful')
            res = TestCaseResult(
                success=True,
                expected_output=test_case.expected_output,
                actual_output=output,
                errors=errors,
            )

            return res

        self.logger.warning('Test case was not successful')
        self.logger.info(
            f'Got: {output}, expected: {test_case.expected_output}',
        )
        return TestCaseResult(
            success=False,
            expected_output=test_case.expected_output,
            actual_output=output,
            errors=errors,
        )

    def _analyze_test_result(
        self,
        state: MainState,
        test_case: TestCase,
        test_result: TestCaseResult,
    ) -> DebugAnalysisResult:

        self.logger.info('Debug Agent: Analyzing errors/outpupts')

        # Construct the input
        inp = {
            'problem_statement': state.problem_statement,
            'code': state.generated_code,
            'test_input': test_case.input_,
            'actual_output': test_result.actual_output,
            'expected_output': test_case.expected_output,
            'error_message': test_result.errors,
            'plan': state.selected_plan,
        }

        json_inp = json.dumps(inp)

        # Prompt the model
        prompt = self._get_prompt('debug_error', json_input=json_inp)

        resp = self.model.prompt(prompt)

        if not resp:
            self.logger.warning('Debug Agent: Got not reponse from the model')

        extracted_json = extract_json_from_markdown(resp)
        if not extracted_json:
            self.logger.debug(f'Got {extracted_json=} for {resp=}')
            self.logger.warning(
                f'Debug Agent: Could not extract json from response {resp=}',
            )

            # Return no fix
            return DebugAnalysisResult(
                decision='no_fix',
                suggestions=None,
                fixed_code=None,
            )

        try:
            json_resp = json.loads(extracted_json[0])
        except json.JSONDecodeError:
            self.logger.warning(
                'Debug Agent: Could not decode JSON from response',
            )
            # Return no fix
            return DebugAnalysisResult(
                decision='no_fix',
                suggestions=None,
                fixed_code=None,
            )

        decision = json_resp.get('decision')
        reason = json_resp.get('reason')

        if decision == 'fix_myself':
            self.logger.info('Debug Agent: Fixing the code myself')
            self.logger.debug(f'Reason to fix the code: {reason}')

            # Get the fixed code
            fixed_code = json_resp.get('fix')
            if not fixed_code:
                self.logger.warning(
                    'Could not extract fixed code from response',
                )
                # Return no fix
                return DebugAnalysisResult(
                    decision='no_fix',
                    suggestions=None,
                    fixed_code=None,
                )

            return DebugAnalysisResult(
                decision='fix_myself',
                suggestions=None,
                fixed_code=fixed_code,
            )

        elif decision == 'delegate':
            suggestion = json_resp.get('suggestion')
            self.logger.info('Debug Agent: Delegating the fix')
            self.logger.debug(f'Reason to delegate the fix: {reason}')
            if not suggestion:
                self.logger.warning(
                    'Could not extract suggestion from response',
                )
                # Return no fix
                return DebugAnalysisResult(
                    decision='no_fix',
                    suggestions=None,
                    fixed_code=None,
                )

            return DebugAnalysisResult(
                decision='delegate',
                suggestions=suggestion,
                fixed_code=None,
            )

        else:
            self.logger.warning(f'Could unseported decision {decision}')
            return DebugAnalysisResult(
                decision='no_fix',
                suggestions=None,
                fixed_code=None,
            )

    def _cycle_plans(self, state: MainState) -> MainState:

        # Move to the next plan in generated_plans (making sure not the
        # current plan is selected)
        if state.generated_plans is None or len(state.generated_plans) == 0:
            self.logger.error('No generated plans to cycle through.')
            return state

        # TODO: Should we sort on confidence?
        next_plan = state.generated_plans.pop(0)
        state.selected_plan = next_plan
        self.logger.info('Debug Agent: Cycling to next plan')
        self.logger.debug(f'Next plan: {next_plan}')
        # Backtrack to coding agent
        state.backtracking_step = 1

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
            test_result = self._run_test_case(
                state.generated_code,
                TestCase(puzzle_input, expected_output),
            )
            if test_result.success:
                self.logger.success('Got expected output, puzzle is solved.')
                # The solution generates the correct output
                # the puzzle is solved!
                state.final_code = state.generated_code
                state.is_solved = True
                return state

            # If the output was None and the errors are None the subprocess
            # raised and there is not a lot of information to debug
            # this means we switch plans
            if (
                test_result.actual_output is None
                and test_result.errors is None
            ):
                self.logger.warning('No output from code, switching plans.')
                return self._cycle_plans(state)

            # If not successful analyze the code and output/errors
            analysis_results = self._analyze_test_result(
                state,
                TestCase(puzzle_input, expected_output),
                test_result,
            )

            if (
                analysis_results.decision == 'fix_myself'
                and analysis_results.fixed_code
            ):
                # Prevent the model from always fixing the code itself
                if self.code_fixes > MAX_CODE_FIXES:
                    self.logger.warning(
                        'Debug Agent: Too many code fixes, '
                        'backtracking to coding.',
                    )
                    state.backtracking_step = 1
                    return state

                self.code_fixes += 1
                state.generated_code = analysis_results.fixed_code
                state.backtracking_step = 0
                return state
            elif (
                analysis_results.decision == 'delegate'
                and analysis_results.suggestions
            ):
                # Prevent the model from always delegating the fix
                if self.delegations > MAX_CODE_FIXES:
                    self.logger.warning(
                        'Debug Agent: Too many delegations, '
                        'cycling plans',
                    )

                    return self._cycle_plans(state)

                self.delegations += 1
                state.debug_suggestions.append(analysis_results.suggestions)
                state.backtracking_step = 1
                return state
            else:
                return self._cycle_plans(state)

        # Try the example test cases from the puzzle
        if len(state.test_cases) > 0:

            successful_tests = 0
            for i, test_case in enumerate(state.test_cases):
                self.logger.info(
                    f'Running example test {i+1}/{len(state.test_cases)}',
                )

                test_result = self._run_test_case(
                    state.generated_code,
                    test_case,
                )

                if not test_result.success:

                    analysis_results = self._analyze_test_result(
                        state,
                        test_case,
                        test_result,
                    )

                    if (
                        analysis_results.decision == 'fix_myself'
                        and analysis_results.fixed_code
                    ):
                        # Prevent the model from always fixing the code itself
                        if self.code_fixes > MAX_CODE_FIXES:
                            self.logger.warning(
                                'Debug Agent: Too many code fixes, '
                                'backtracking to coding.',
                            )
                            state.backtracking_step = 1
                            return state

                        self.code_fixes += 1
                        state.generated_code = analysis_results.fixed_code
                        state.backtracking_step = 0
                        return state
                    elif (
                        analysis_results.decision == 'delegate'
                        and analysis_results.suggestions
                    ):
                        # Prevent the model from always delegating the fix
                        if self.delegations > MAX_CODE_FIXES:
                            self.logger.warning(
                                'Debug Agent: Too many delegations, '
                                'cycling plans',
                            )

                            return self._cycle_plans(state)

                        self.delegations += 1
                        state.debug_suggestions.append(
                            analysis_results.suggestions,
                        )
                        state.backtracking_step = 1
                        return state
                    else:
                        return self._cycle_plans(state)

                else:
                    successful_tests += 1

            if successful_tests == len(state.test_cases):
                self.logger.info('All example tests cases were successful')
                if expected_output is None:
                    self.logger.info(
                        'No expected output was given and all tests succeeded,'
                        ' considering the solution correct',
                    )
                    state.is_solved = True
                    state.final_code = state.generated_code
            else:
                self.logger.warning(
                    'Test cases failed, debugging did not work',
                )
        return state
