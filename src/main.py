import os

from dotenv import load_dotenv
from models.gemini_model import GeminiLanguageModel

if __name__ == '__main__':

    load_dotenv()

    # model = OpenAILanguageModel(
    #     model_name='gpt-4o',
    #     api_key=os.getenv('OPENAI_API_KEY') or '',
    # )

    # model = DeepseekLanguageModel(
    #     model_name='deepseek-chat',
    #     api_key=os.getenv('DEEPSEEK_API_KEY') or '',
    # )

    model = GeminiLanguageModel(
        model_name='gemini-2.0-flash',
        api_key=os.getenv('GEMINI_API_KEY') or '',
    )

    resp = model.prompt(
        'Hello, how are you? And what model are you?',
    )

    print(resp)
