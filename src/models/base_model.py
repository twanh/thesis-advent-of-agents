from abc import ABC
from abc import abstractmethod

from loguru import logger


class BaseLanguageModel(ABC):
    """Abstract base class for language models"""

    def __init__(
            self,
            model_name: str,
            api_key: str,
            system_prompt: str | None = None,
    ):
        """
        Initialize the language model with the model name and API key.

        Args:
            model_name (str): The name of the model.
            api_key (str): The API key for the model.
            system_prompt (str|None): The system prompt for the model.
        """

        self.model_name = model_name
        self.api_key = api_key
        self.logger = logger.bind(model=self.model_name)
        self.system_prompt = system_prompt

        # TODO: If necessary add **kwargs and save to config?

    def set_system_prompt(self, text: str) -> None:
        """
        Set the system prompt for the model.

        Args:
            text (str): The system prompt.

        Returns:
            None
        """
        self.system_prompt = text

    @abstractmethod
    def prompt(self, text: str) -> str:
        """
        Prompt the language model with a text and return the response.

        Args:
            text (str): The text to prompt the model with.

        Returns:
            str: The response from the model.
        """

        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(model_name='{self.model_name}')"
