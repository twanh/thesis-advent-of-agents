import re
from typing import Any


def extract_json_from_markdown(model_response: str) -> list[Any]:
    # If the response starts with { it means the full response is json
    if model_response.startswith('{'):
        return [model_response]
    pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, model_response)
    return matches


def extract_markdown_from_response(response_text: str) -> list[str]:

    pattern = r'```markdown\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, response_text)
    return matches
