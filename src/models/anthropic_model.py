from anthropic import Anthropic
from models.base_model import BaseLanguageModel


class AnthropicLanguageModel(BaseLanguageModel):

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client = Anthropic(api_key=api_key)

    def prompt(self, text: str) -> str:

        response = self.client.messages.create(
            model=self.model_name,
            messages=[
                {
                    'role': 'user',
                    'content': text,
                },
            ],
            max_tokens=1024,
        )

        return response.content
