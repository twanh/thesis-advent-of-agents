import re
from typing import Any


def extract_json_from_markdown(markdown_text: str) -> list[Any]:
    pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, markdown_text)
    return matches


def extract_markdown_from_response(response_text: str) -> list[str]:

    pattern = r'```markdown\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, response_text)
    return matches
