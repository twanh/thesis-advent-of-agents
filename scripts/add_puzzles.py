import re
import argparse
import os
import sys
import dotenv
from tqdm import tqdm

from loguru import logger

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src/')
sys.path.append(PROJECT_ROOT)

from core.state import MainState
from agents.pre_processing_agent import PreProcessingAgent
from models.gemini_model import GeminiLanguageModel
from utils.util_types import Puzzle
from core.retreival import PuzzleData
from core.retreival import PuzzleRetreival


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


def _extract_year_day(puzzle_path: str) -> tuple[str,str]:


    pattern = r".*/(\d{4})/day_(\d+)_part_1\.txt"
    match = re.match(pattern, puzzle_path)
    if match:
        year, day = match.groups()
        return (year, day)

    tqdm.write(f"Error: could not extract year,day from: {puzzle_path}")
    return '', ''


def _main() -> int:

    parser = argparse.ArgumentParser(
        description="Add puzzles to the database",
    )

    parser.add_argument(
        'puzzle_dir',
        type=str,
        help='Directory containing the puzzles in format: [year]/day_[day]_part_1.txt',
    )

    parser.add_argument(
        'db',
        type=str,
        help='Database to connect to (psycopg2 connection string)',
    )


    # Load environment variables from .env file if not given in command line
    dotenv.load_dotenv()
    args = parser.parse_args()

    # Create language model
    model = GeminiLanguageModel(
        api_key=os.getenv("GEMINI_API_KEY"),
        model_name='gemini-2.0-flash'
    )

    # Create agent
    agent = PreProcessingAgent(
        agent_name='pre_processing_agent',
        model=model,
    )

    # Create retreival
    retreival_system = PuzzleRetreival(
        connection_string=args.db,
        openai_key = os.getenv("OPENAI_API_KEY"),
        pre_processing_agent=agent,
    )

    retreival_system.init_db()

    # Get all the puzzles
    all_puzzles = get_puzzle_paths(args.puzzle_dir)

    # Create embeddings for the puzzles & add directly to the database
    for puzzle in tqdm(all_puzzles):
        year, day = _extract_year_day(puzzle)

        if not year or not day:
            tqdm.write(f"Skipping puzzle: {puzzle}")
            continue

        tqdm.write(f"Loading puzzle: {puzzle}")
        # Load the puzzles
        with open(puzzle, 'r') as f:
            puzzle_desc = f.read()

        puzzle = Puzzle(
            description=puzzle_desc,
            day = day,
            year=year,
            solution=None
        )

        # Add puzzle
        puzzle_id = retreival_system.add_puzzle(puzzle)
        tqdm.write(f"Added puzzle with id: {puzzle_id}")


    return 0


if __name__ == "__main__":

    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level='WARNING')

    raise SystemExit(_main())
