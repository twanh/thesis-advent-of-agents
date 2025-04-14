import re


def extract_json_from_markdown(markdown_text):
    pattern = r'```json\s*([\s\S]*?)\s*```'
    matches = re.findall(pattern, markdown_text)
    return matches
