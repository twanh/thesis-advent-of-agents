from abc import ABC
from abc import abstractmethod

from core.state import MainState
from loguru import logger
from models.base_model import BaseLanguageModel
from prompts.prompts import PROMPTS


class BaseAgent(ABC):
    """Base class for agents"""

    def __init__(self, agent_name: str, model: BaseLanguageModel):

        self.name = agent_name
        self.model = model
        self.logger = logger.bind(agent_name=agent_name)

    def _get_prompt(self, prompt_name: str, **kwargs) -> str:

        try:
            formatted_prompt = PROMPTS.get(prompt_name, '').format(**kwargs)
        except KeyError as e:
            self.logger.error(f'Missing key in prompt: {e}')
            formatted_prompt = ''

        return formatted_prompt

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
        logger.debug(
            f"Loaded prompt: {self._get_prompt('test', agent_name=self.name)}",
        )
        return state
