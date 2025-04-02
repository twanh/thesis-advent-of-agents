from typing import Any

from agents.base_agent import BaseAgent
from core.state import MainState
from loguru import logger
from utils.util_types import AgentSettings


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

        state = initial_state
        current_agent_index = 0
        while current_agent_index < len(self.agents):

            current_agent, current_agent_settings = self.agents[current_agent_index]  # noqa: E501

            if current_agent_settings.enabled:
                self.logger.info('Running agent: {}', current_agent.name)
                updated_state = current_agent.process(state)
                self.logger.debug(updated_state)

            current_agent_index += 1

        return state
