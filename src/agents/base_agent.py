from abc import ABC
from abc import abstractmethod

from core.state import MainState
from models.base_model import BaseLanguageModel


class BaseAgent(ABC):
    """Base class for agents"""

    def __init__(self, agent_name: str, model: BaseLanguageModel):

        self.name = agent_name
        self.model = model

    @abstractmethod
    def process(self, state: MainState) -> MainState:
        """
        Process the state and return the response/updated state.

        Args:
            state (dict): The state to process.

        Returns:
            dict: The updated state after the agent's processing.
        """

        pass


class MockAgent(BaseAgent):

    def process(self, state: MainState) -> MainState:
        # Create mock Agent
        return state
