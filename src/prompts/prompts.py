import os


def _load_prompt_from_file(prompt_name: str) -> str:
    with open(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            'raw',
            f'{prompt_name}.txt',
        ),
    ) as f:
        return f.read()


PROMPTS = {
    'test': _load_prompt_from_file('test'),
}
