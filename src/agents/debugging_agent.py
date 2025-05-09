import copy
import json
import os
import subprocess
import tempfile
from enum import Enum
from typing import NamedTuple

from agents.base_agent import BaseAgent
from core.state import MainState
from models.base_model import BaseLanguageModel
from utils.util_types import TestCase
from utils.utils import extract_json_from_markdown

MAX_CODE_FIXES = 2
MAX_DELEGATION_FIXES = 2


class DebugDecision(Enum):

    FIX = 'fix'
    DELEGATE = 'delegate'
    NO_FIX = 'no_fix'
    CYCLE = 'cycle'


class AnalysisResult(NamedTuple):

    decision: DebugDecision
    suggestions: str | None
    fixed_code: str | None


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

    def _mark_solved(self, state: MainState) -> MainState:
        state.final_code = state.generated_code
        state.is_solved = True
        return state

    def _apply_fix(
        self,
        state: MainState,
        fixed_code: str,
        suggestion: str,
    ) -> MainState:

        # Check if the code is fixed
        if fixed_code == state.generated_code:
            self.logger.warning('Debug Agent: No fix applied')
            return state

        # Check if we have reached the maximum number of fixes
        if self.code_fixes >= MAX_CODE_FIXES:
            self.logger.warning('Debug Agent: Maximum number of fixes reached')
            # Switch to delegation
            # but there is no suggestion since no suggestion was made
            return self._apply_delegation(state, suggestion)

        # Apply the fix
        self.logger.info('Debug Agent: Applying fix')
        state.generated_code = fixed_code
        self.code_fixes += 1

        return state

    def _apply_delegation(
        self,
        state: MainState,
        suggestion: str,
    ) -> MainState:

        # Check if we have reached the maximum number of delegations
        if self.delegations >= MAX_DELEGATION_FIXES:
            self.logger.warning(
                'Debug Agent: Maximum number of delegations reached',
            )
            return state

        # Apply the delegation
        self.logger.info('Debug Agent: Applying delegation')
        self.logger.debug(f'Got suggestion: {suggestion}')
        state.debug_suggestions.append(suggestion)
        self.delegations += 1
        # Esnure backtracking to codeing agents
        # which will look at the suggestion
        state.backtracking_step = 1

        return state

    def _apply_decision(
        self,
        state: MainState,
        result: AnalysisResult,
    ) -> MainState:

        if result.decision == DebugDecision.FIX:
            self.logger.info('Debug Agent: Fixing code')
            return self._apply_fix(
                state,
                result.fixed_code or '',
                result.suggestions or '',
            )
        elif result.decision == DebugDecision.DELEGATE:
            self.logger.info('Debug Agent: Delegating to model')
            self.delegations += 1
            return self._apply_delegation(state, result.suggestions or '')
        elif result.decision == DebugDecision.CYCLE:
            self.logger.info('Debug Agent: Cycling plans')
            return self._cycle_plans(state)
        elif result.decision == DebugDecision.NO_FIX:

            self.logger.info('Debug Agent: No fix found')
            # If we have cycled through all the plans
            # then we can stop the agent
            if (
                state.generated_plans is None
                or len(state.generated_plans) == 0
            ):
                self.logger.warning(
                    'Debug Agent: No fix found and no more plans to cycle',
                )
                return state

            # Cycle the plans
            return self._cycle_plans(state)
        else:
            # Unknown decision, do nothing
            # This should not happen
            return state

    def _analyze_failure(
        self,
        state: MainState,
        test_case: TestCase,
        result: TestCaseResult,
    ) -> AnalysisResult:
        """
        Analyze the failure and return a decision on what to do next.
        """

        # Construct the input
        inp = {
            'problem_statement': state.problem_statement,
            'code': state.generated_code,
            'test_input': test_case.input_,
            'actual_output': result.actual_output,
            'expected_output': test_case.expected_output,
            'error_message': result.errors,
            'plan': state.selected_plan,
        }
        json_inp = json.dumps(inp)

        # Prompt the model
        prompt = self._get_prompt('debug_error', json_input=json_inp)
        resp = self.model.prompt(prompt)
        if not resp:
            self.logger.warning('Debug Agent: Got not reponse from the model')

        # Extract the json from the response
        extracted_json = extract_json_from_markdown(resp)
        if not extracted_json:
            self.logger.debug(f'Got {extracted_json=} for {resp=}')
            self.logger.warning(
                'Debug Agent: Could not extract json from response.',
            )
            # Return no fix
            return AnalysisResult(
                decision=DebugDecision.NO_FIX,
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
            return AnalysisResult(
                decision=DebugDecision.NO_FIX,
                suggestions=None,
                fixed_code=None,
            )

        # Get the decision
        decision = json_resp.get('decision')
        reason = json_resp.get('reason')

        self.logger.debug(f'Analysis result: {decision=} {reason=}')

        if decision == 'fix_myself':
            fixed_code = json_resp.get('fix')
            if not fixed_code:
                self.logger.warning(
                    'Debug Agent: Could not extract fixed code from response',
                )

                # Return no fix since no fix could be generated
                # how to handle this is up to the apply_decision method
                return AnalysisResult(
                    decision=DebugDecision.NO_FIX,
                    suggestions=None,
                    fixed_code=None,
                )

            # Get the suggestions
            suggestions = json_resp.get('suggestions', '')
            return AnalysisResult(
                decision=DebugDecision.FIX,
                suggestions=suggestions,
                fixed_code=fixed_code,
            )

        elif decision == 'delegate':
            suggestion = json_resp.get('suggestion')
            if not suggestion:
                self.logger.warning(
                    'Debug Agent: Could not extract suggestion from response',
                )
                # Return no fix
                return AnalysisResult(
                    decision=DebugDecision.NO_FIX,
                    suggestions=None,
                    fixed_code=None,
                )

            return AnalysisResult(
                decision=DebugDecision.DELEGATE,
                suggestions=suggestion,
                fixed_code=None,
            )

        elif decision == 'plan':
            # Cycle the plans
            return AnalysisResult(
                decision=DebugDecision.CYCLE,
                suggestions=None,
                fixed_code=None,
            )
        else:
            self.logger.warning(f'Unsupported decision: {decision}')
            # Return no fix
            return AnalysisResult(
                decision=DebugDecision.NO_FIX,
                suggestions=None,
                fixed_code=None,
            )

    def _validate_requirements(self, state: MainState) -> bool:
        """
        Check that all the requirements are met to run the agent.
        """

        # Check that all the requirements to run a valid
        puzzle_input = self.settings.get('puzzle_input')
        if not puzzle_input:
            self.logger.error('Debugger requires puzzle input to run.')
            raise ValueError('No puzze_input in settings')

        if state.generated_code is None:
            self.logger.error('Debugger requires code to run.')
            return False

        return True

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

    def _run_test(self, code: str, test_case: TestCase) -> TestCaseResult:

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
        if not self._validate_requirements(state):
            # There is no code written so backtrack to the coding agent
            state.backtracking_step = 1
            return state

        # If we know the expected output for the puzzle
        # then immediately try if it works
        expected_output = self.settings.get('expected_output', None)
        if expected_output is not None:
            # Try the test case
            # checked in _validate_requirements
            assert self.settings['puzzle_input'] is not None
            test_case = TestCase(
                self.settings['puzzle_input'], expected_output,
            )
            assert state.generated_code is not None
            result = self._run_test(state.generated_code, test_case)

            # The solution is correct
            if result.success:
                self.logger.success('Got expected output, puzzle is solved')
                return self._mark_solved(state)

            # Execution failed
            # If both are None nothing was returned or printed to screen
            if result.actual_output is None and result.errors is None:
                self.logger.warning('No output from code, cycling plans')
                return self._cycle_plans(state)

            # Analyze the failure and apply the decision
            failure_analysis = self._analyze_failure(state, test_case, result)
            return self._apply_decision(state, failure_analysis)

        # Run the example tests if there is no expected outcome
        if not state.test_cases:
            self.logger.warning('No test cases to run')
            return state

        # Go through all the test cases
        # if all succeed the solution is considered correct (since there
        # is not expected output to test)
        # If a failure is found then the failure get's analyzed
        # and the decision applied
        n_successful = 0
        for test_case in state.test_cases:
            assert state.generated_code is not None
            result = self._run_test(state.generated_code, test_case)

            if result.success:
                n_successful += 1
                continue

            # Execution failed
            # If both are None nothing was returned or printed to screen
            if result.actual_output is None and result.errors is None:
                self.logger.warning('No output from code, cycling plans')
                return self._cycle_plans(state)

            failure_analysis = self._analyze_failure(state, test_case, result)
            # Apply the decision
            return self._apply_decision(state, failure_analysis)

        if n_successful == len(state.test_cases):
            self.logger.success('All test cases passed, puzzle is solved')
            return self._mark_solved(state)

        return state
