from anthropic import Anthropic
from models.base_model import BaseLanguageModel


class AnthropicLanguageModel(BaseLanguageModel):

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client = Anthropic(api_key=api_key)

    def prompt(self, text: str) -> str:

        try:

            self.logger.debug(
                (
                    f'Prompting {self} with prompt: '
                    f'{self.system_prompt=} {text=}'
                ),
            )

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

            if response.content is None:
                self.logger.warning(
                    'Received unexpected None response from Anthropic',
                )
                return ''

            return response.content

        except Exception as e:
            self.logger.error(f'Error while prompting {self}: {e}')
            return ''
