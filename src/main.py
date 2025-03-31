import os

from dotenv import load_dotenv
from models.deepseek_model import DeepseekLanguageModel

if __name__ == '__main__':

    load_dotenv()

    # model = OpenAILanguageModel(
    #     model_name='gpt-4o',
    #     api_key=os.getenv('OPENAI_API_KEY') or '',
    # )

    model = DeepseekLanguageModel(
        model_name='deepseek-chat',
        api_key=os.getenv('DEEPSEEK_API_KEY') or '',
    )

    resp = model.prompt(
        'Hello, how are you? An what model are you?',
        [
            {
                'role': 'system',
                'content': (
                    'You are an AI model called Advent Of Agents'
                ),
            },
        ],
    )
    print(resp)
