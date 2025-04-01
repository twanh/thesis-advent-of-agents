from typing import Any

from agents.base_agent import BaseAgent
from core.state import MainState


class Orchestrator:

    def __init__(
        self,
        agents: dict[str, BaseAgent],
        agent_config: dict[str, dict[str, Any]],
        config: dict[str, Any],
    ):
        """
        Initialize the orchestrator with the agents and configuration.

        Args:
            agents dict[str, BaseAgent]:
                A dictionary mapping agent names to their instantiated objects.
            agent_config (dict[str, dict[str, Any]]):
                A dictionary mapping agent names to their configuration.
                (e.g: {'coding_agent': {'enabled': True}}).
            config (dict[str, Any]): The configuration for the orchestrator.
        """

        self.agents = agents
        self.agent_config = agent_config
        self.config = config

    def _agent_is_enabled(self, agent_name: str) -> bool:
        """
        Check if the agent is enabled in the configuration.

        Args:
            agent_name (str): The name of the agent.

        Returns:
            bool: True if the agent is enabled, False otherwise
        """

        return self.agent_config.get(agent_name, {}).get('enabled', False)

    def solve_puzzle(self, initial_state: MainState) -> MainState:
        """
        Solve the puzzle using the agents.

        Args:
            initial_state (MainState): The initial state of the system.

        Returns:
            MainState: The final state of the system after processing.
        """

        state = initial_state

        for agent_name, agent in self.agents.items():
            if self.agent_config[agent_name].get('enabled', False):
                state.current_step = agent_name
                updated_state = agent.process(state)
                # TODO: Propper error handling for agents
                if updated_state is None:
                    raise ValueError(f'Agent {agent_name} returned None')
                state = updated_state

        return state
