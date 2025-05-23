from abc import ABC
from abc import abstractmethod
from typing import Any

from core.state import MainState
from loguru import logger
from models.base_model import BaseLanguageModel
from prompts.prompts import PROMPTS


class BaseAgent(ABC):
    """Base class for agents"""

    def __init__(
            self,
            agent_name: str,
            model: BaseLanguageModel,
            **settings: Any,
    ):

        self.name = agent_name
        self.model = model
        self.logger = logger.bind(agent_name=agent_name)
        # Sometimes the (json) response is invalid
        # so we have to retry a few times
        # NOTE: The retries are for all errors that need retries
        #       so there is a hard MAX of 3 retries
        self.invalid_response_retries = 0
        self.max_invalid_response_retries = 3
        self.settings = settings

    def _get_prompt(self, prompt_name: str, **kwargs) -> str:

        try:
            raw_prompt = PROMPTS.get(prompt_name, None)
            if raw_prompt is None:
                self.logger.warning(f'Could not find prompt {prompt_name=}')
                return ''
            formatted_prompt = raw_prompt.format(**kwargs)

        except KeyError as e:
            self.logger.error(f'Missing key in prompt: {e}')
            formatted_prompt = ''

        return formatted_prompt

    def _invalid_response_retry(self, state: MainState) -> MainState:
        """
        Retry the agent if the response is invalid.

        Args:
            state (dict): The state to process.

        Returns:
            dict: The updated state after the agent's processing.
        """

        self.invalid_response_retries += 1
        if self.invalid_response_retries > self.max_invalid_response_retries:
            self.logger.error(
                f'Max retries reached for {self.name}. '
                'Returning original state.',
            )
            return state

        self.logger.warning(
            f'Retrying {self.invalid_response_retries}/{self.max_invalid_response_retries} for {self.name}',  # noqa: E501
        )
        # Retry the agent
        return self.process(state)

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
