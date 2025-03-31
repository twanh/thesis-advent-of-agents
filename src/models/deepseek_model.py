from models.openai_model import OpenAILanguageModel


class DeepseekLanguageModel(OpenAILanguageModel):
    """
    A language model for the Deepseek API.

    Note: the deepseek API uses the same API as the OpenAI API, so we can
    inherit from the OpenAILanguageModel.
    """

    def __init__(self, model_name: str, api_key: str):
        super().__init__(model_name, api_key)

        self.client.base_url = 'https://api.deepseek.com'
