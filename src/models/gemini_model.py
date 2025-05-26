from google import genai
from google.genai import types
from models.base_model import BaseLanguageModel


class GeminiLanguageModel(BaseLanguageModel):

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client = genai.Client(api_key=api_key)

    def prompt(self, text: str) -> str:

        try:
            self.logger.debug(
                (
                    f'Prompting {self} with prompt: '
                    f'{self.system_prompt=} {text=}'
                ),
            )

            response = self.client.models.generate_content(
                model=self.model_name,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_prompt,
                ),
                contents=text,
            )

            if response.text is None:
                self.logger.warning(
                    'Received unexpected None response from Google',
                )
                return ''

            return response.text

        except Exception as e:
            self.logger.error(f'Error while prompting {self}: {e}')
            return ''
