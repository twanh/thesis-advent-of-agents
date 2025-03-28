from models.base_model import BaseLanguageModel
from openai import OpenAI


class OpenAILanguageModel(BaseLanguageModel):

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client = OpenAI(api_key=api_key)

    def prompt(
        self,
        text: str,
        context: list[dict[str, str]] | None = None,
    ) -> str:

        prompt = [{'role': 'user', 'content': text}]
        if context is not None:
            # Prepent the context to the prompt
            prompt = context + prompt

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
                    f'Warning: Received unexpected response format from\
                    OpenAI: {response}',
                )
                return ''

        except Exception as e:
            self.logger.error(f'Error while prompting model: {e}')
            # TODO: Handle error better?
            return ''
