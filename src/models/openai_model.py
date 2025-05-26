from models.base_model import BaseLanguageModel
from openai import OpenAI


class OpenAILanguageModel(BaseLanguageModel):

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client = OpenAI(api_key=api_key)

    def prompt(
        self,
        text: str,
    ) -> str:

        prompt = [{'role': 'user', 'content': text}]
        if self.system_prompt is not None:
            prompt = [
                {'role': 'system', 'content': self.system_prompt},
            ] + prompt

        self.logger.debug(f'Prompting model with: {prompt}')

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=prompt,  # type: ignore
            )

            if response.choices and response.choices[0].message:
                return response.choices[0].message.content or ''
            else:
                self.logger.warning(
                    (
                        'Received unexpected response format from OpenAI: '
                        f'{response}'
                    ),
                )
                return ''

        except Exception as e:
            self.logger.error(f'Error while prompting {self}: {e}')
            # TODO: Handle error better?
            return ''
