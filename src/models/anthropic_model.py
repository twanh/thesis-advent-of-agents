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
                max_tokens=8192,
            )

            if not response.content:
                self.logger.warning(
                    'Received unexpected None response from Anthropic',
                )
                return ''

            if not hasattr(response.content[0], 'text'):
                self.logger.debug(
                    f'No text in response content: {response.content}',
                )
                return ''

            return getattr(response.content[0], 'text')

        except Exception as e:
            self.logger.error(f'Error while prompting {self}: {e}')
            return ''
