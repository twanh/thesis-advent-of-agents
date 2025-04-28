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
    'pre_processing': _load_prompt_from_file('pre_processing'),
    'retreival_rank_solutions': _load_prompt_from_file('retreival_rank_solutions'),  # noqa: E501
}
