import os

from dotenv import load_dotenv
from models.openai_model import OpenAILanguageModel

if __name__ == '__main__':

    load_dotenv()

    model = OpenAILanguageModel(
        model_name='gpt-4o',
        api_key=os.getenv('OPENAI_API_KEY') or '',
    )

    resp = model.prompt(
        'Hello, how are you?',
        [
            {
                'role': 'developer',
                'content': (
                    'You are an assistant that is not doing"'
                    'well at the moment.'
                ),
            },
        ],
    )
    print(resp)
