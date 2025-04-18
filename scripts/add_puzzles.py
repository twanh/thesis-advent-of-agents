import argparse
import os
import re
import sys

import dotenv
from agents.pre_processing_agent import PreProcessingAgent
from core.retreival import PuzzleRetreival
from loguru import logger
from models.gemini_model import GeminiLanguageModel
from tqdm import tqdm
from utils.util_types import Puzzle

PROJECT_ROOT = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__),
    ), '../src/',
)
sys.path.append(PROJECT_ROOT)


def get_puzzle_paths(puzzles_path: str) -> list[str]:

    puzzle_paths = []
    for year in os.listdir(puzzles_path):
        year_path = os.path.join(puzzles_path, year)
        if os.path.isdir(year_path):
            for day in os.listdir(year_path):
                day_path = os.path.join(year_path, day)
                if os.path.isfile(day_path):
                    if day_path.endswith('.txt'):
                        puzzle_paths.append(day_path)
    return puzzle_paths


def _extract_year_day(puzzle_path: str) -> tuple[str, str]:

    pattern = r'.*/(\d{4})/day_(\d+)_part_1\.txt'
    match = re.match(pattern, puzzle_path)
    if match:
        year, day = match.groups()
        return (year, day)

    tqdm.write(f'Error: could not extract year,day from: {puzzle_path}')
    return '', ''


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Add puzzles to the database',
    )
    parser.add_argument(
        'puzzle_dir',
        type=str,
        help=(
            'Directory containing puzzles in format:'
            '[year]/day_[day]_part_1.txt'
        ),
    )
    parser.add_argument(
        'db',
        type=str,
        help='Database connection string (psycopg2 format)',
    )
    dotenv.load_dotenv()
    return parser.parse_args()


def _setup_retrieval_system(db_connection: str) -> PuzzleRetreival:
    model = GeminiLanguageModel(
        api_key=os.getenv('GEMINI_API_KEY'),
        model_name='gemini-2.0-flash',
    )
    agent = PreProcessingAgent(
        agent_name='pre_processing_agent',
        model=model,
    )
    return PuzzleRetreival(
        connection_string=db_connection,
        openai_key=os.getenv('OPENAI_API_KEY'),
        pre_processing_agent=agent,
    )


def _process_puzzle(
    puzzle_path: str,
    retrieval: PuzzleRetreival,
) -> int | None:
    year, day = _extract_year_day(puzzle_path)
    if not year or not day:
        tqdm.write(f'Skipping puzzle (invalid format): {puzzle_path}')
        return None

    tqdm.write(f'Loading puzzle: {puzzle_path}')
    with open(puzzle_path, 'r') as f:
        puzzle_desc = f.read()

    puzzle = Puzzle(
        description=puzzle_desc,
        day=day,
        year=year,
        solution=None,
    )
    puzzle_id = retrieval.add_puzzle(puzzle)
    tqdm.write(f'Added puzzle with id: {puzzle_id}')
    return puzzle_id


def _main() -> int:
    args = _parse_args()
    retrieval = _setup_retrieval_system(args.db)
    retrieval.init_db()

    puzzle_paths = get_puzzle_paths(args.puzzle_dir)
    for puzzle_path in tqdm(puzzle_paths):
        _process_puzzle(puzzle_path, retrieval)

    return 0


if __name__ == '__main__':

    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level='WARNING')

    raise SystemExit(_main())
