import logging
from abc import ABC
from abc import abstractmethod


class BaseLanguageModel(ABC):
    """Abstract base class for language models"""

    def __init__(self, model_name: str, api_key: str):
        """
        Initialize the language model with the model name and API key.

        Args:
            model_name (str): The name of the model.
            api_key (str): The API key for the model.
        """

        self.model_name = model_name
        self.api_key = api_key
        self.logger = logging.getLogger(f'model.{self.model_name}')

        # TODO: If nessesary add **kwargs and save to config?

    @abstractmethod
    def prompt(self, text: str, context: list[dict[str, str]] | None) -> str:
        """
        Promt the language model with a text and return the response.

        Args:
            text (str): The text to promt the model with.
            context (list[dict[str, str]] | None): The context for the model
                (for example system messages).

        Returns:
            str: The response from the model.
        """

        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(model_name='{self.model_name}')"
