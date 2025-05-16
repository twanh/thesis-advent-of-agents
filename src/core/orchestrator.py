from pprint import pformat
from typing import Any

from agents.base_agent import BaseAgent
from core.state import MainState
from loguru import logger
from utils.util_types import AgentSettings

MAX_DEBUG_ATTEMPTS = 5


class Orchestrator:

    def __init__(
        self,
        agents: tuple[tuple[BaseAgent, AgentSettings], ...],
        config: dict[str, Any],
    ):
        """
        Initialize the orchestrator with the agents and configuration.

        Args:
            agents tuple[dict[str, BaseAgent]]:
                A tuple containing the agents and the settings,
                in exection order.
            config (dict[str, Any]): The configuration for the orchestrator.
        """

        self.agents = agents
        # TODO: Create the settings for the orchestrator
        #       (e,g.: # debug tries, etc)
        self.config = config
        self.logger = logger.bind(name='orchestrator')

    def solve_puzzle(self, initial_state: MainState) -> MainState:
        """
        Solve the puzzle using the agents.

        Args:
            initial_state (MainState): The initial state of the system.

        Returns:
            MainState: The final state of the system after processing.
        """

        # For each agent runn the process
        # - update the state with the agent result
        # - debug agent: can backtrack

        # NOTE: Should this use deepcopy?
        state = initial_state
        current_agent_index = 0
        while current_agent_index < len(self.agents):

            current_agent, current_agent_settings = self.agents[current_agent_index]  # noqa: E501

            if current_agent_settings.enabled:
                self.logger.info('Running agent: {}', current_agent.name)
                state = current_agent.process(state)
                self.logger.trace(pformat(state))

            if state.is_solved:
                self.logger.success('Puzzle solved!')
                break

            if state.debug_attempts > MAX_DEBUG_ATTEMPTS:
                self.logger.warning(
                    f'Max debug debug_attempts {MAX_DEBUG_ATTEMPTS} reached',
                )
                break

            # If the agent is the debugging agents
            # then we need to backtrack to the coding agent
            if (
                current_agent_settings.can_debug
                and current_agent_settings.enabled
            ):
                state.debug_attempts += 1
                # TODO: Should we check if the debugging agent
                # is the one before coding?
                self.logger.info(
                    f'Backtracking by {state.backtracking_step} step',
                )
                current_agent_index -= state.backtracking_step
                continue

            current_agent_index += 1

        return state
