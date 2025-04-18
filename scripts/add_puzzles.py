import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import dotenv
from loguru import logger
from tqdm import tqdm

PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../src/')
sys.path.append(PROJECT_ROOT)

from agents.pre_processing_agent import PreProcessingAgent
from core.retreival import PuzzleRetreival
from models.gemini_model import GeminiLanguageModel
from utils.util_types import Puzzle


def get_puzzle_paths(puzzles_path: str) -> List[str]:
    """Get all puzzle file paths from the given directory.
    
    Args:
        puzzles_path: Path to directory containing puzzle files organized by year/day.
        
    Returns:
        List of full paths to puzzle files.
    """
    puzzle_paths = []
    for year in os.listdir(puzzles_path):
        year_path = Path(puzzles_path) / year
        if year_path.is_dir():
            for day_file in year_path.iterdir():
                if day_file.is_file() and day_file.suffix == '.txt':
                    puzzle_paths.append(str(day_file))
    return puzzle_paths


def _extract_year_day(puzzle_path: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract year and day from puzzle file path.
    
    Args:
        puzzle_path: Path to puzzle file expected to be in format '.../YYYY/day_DD_part_1.txt'
        
    Returns:
        Tuple of (year, day) or (None, None) if pattern doesn't match.
    """


    pattern = r".*/(\d{4})/day_(\d+)_part_1\.txt"
    match = re.match(pattern, puzzle_path)
    if match:
        year, day = match.groups()
        return (year, day)

    tqdm.write(f"Error: could not extract year,day from: {puzzle_path}")
    return '', ''


def _parse_args() -> argparse.Namespace:
    """Parse and return command line arguments."""
    parser = argparse.ArgumentParser(
        description="Add puzzles to the database",
    )
    parser.add_argument(
        'puzzle_dir',
        type=str,
        help='Directory containing puzzles in format: [year]/day_[day]_part_1.txt',
    )
    parser.add_argument(
        'db',
        type=str,
        help='Database connection string (psycopg2 format)',
    )
    dotenv.load_dotenv()
    return parser.parse_args()


def _setup_retrieval_system(db_connection: str) -> PuzzleRetreival:
    """Initialize and return the puzzle retrieval system."""
    model = GeminiLanguageModel(
        api_key=os.getenv("GEMINI_API_KEY"),
        model_name='gemini-2.0-flash'
    )
    agent = PreProcessingAgent(
        agent_name='pre_processing_agent',
        model=model,
    )
    return PuzzleRetreival(
        connection_string=db_connection,
        openai_key=os.getenv("OPENAI_API_KEY"),
        pre_processing_agent=agent,
    )


def _process_puzzle(puzzle_path: str, retrieval: PuzzleRetreival) -> Optional[int]:
    """Process and add a single puzzle to the database.
    
    Returns:
        The puzzle ID if successful, None otherwise.
    """
    year, day = _extract_year_day(puzzle_path)
    if not year or not day:
        tqdm.write(f"Skipping puzzle (invalid format): {puzzle_path}")
        return None

    tqdm.write(f"Loading puzzle: {puzzle_path}")
    with open(puzzle_path, 'r') as f:
        puzzle_desc = f.read()

    puzzle = Puzzle(
        description=puzzle_desc,
        day=day,
        year=year,
        solution=None
    )
    puzzle_id = retrieval.add_puzzle(puzzle)
    tqdm.write(f"Added puzzle with id: {puzzle_id}")
    return puzzle_id


def _main() -> int:
    """Main entry point for the script."""
    args = _parse_args()
    retrieval = _setup_retrieval_system(args.db)
    retrieval.init_db()

    puzzle_paths = get_puzzle_paths(args.puzzle_dir)
    for puzzle_path in tqdm(puzzle_paths):
        _process_puzzle(puzzle_path, retrieval)

    return 0


if __name__ == "__main__":

    # Set up logging
    logger.remove()
    logger.add(sys.stderr, level='WARNING')

    raise SystemExit(_main())
