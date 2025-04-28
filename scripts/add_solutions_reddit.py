import argparse
import json
import os
import sys

import dotenv
from core.retreival import PuzzleRetreival
from core.retreival import SolutionData
from tqdm import tqdm


PROJECT_ROOT = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__),
    ), '../src/',
)
sys.path.append(PROJECT_ROOT)


def _main() -> int:

    parser = argparse.ArgumentParser(
        description='Import Advent of Code solutions from a JSON file\
        into the database.',
    )
    parser.add_argument(
        'json_file',
        type=str,
        help='Path to the JSON file containing solutions.',
    )

    parser.add_argument(
        'db',
        type=str,
        help='Database connection string (psycopg2 format)',
    )

    args = parser.parse_args()

    dotenv.load_dotenv()

    retreival = PuzzleRetreival(
        connection_string=args.db,
        openai_key=os.getenv('OPENAI_API_KEY'),
    )

    retreival.init_db()

    with open(args.json_file, 'r') as f:
        solutions = json.load(f)

    r_solutions = solutions.get('solutions', [])
    print(f'Found {len(r_solutions)}')
    added = 0
    for solution in tqdm(r_solutions):

        sol_data = SolutionData(
            code=solution['code'],
            author=solution['author'],
            source='reddit',
            puzzle_day=solution['thread_info']['day'],
            puzzle_year=solution['thread_info']['year'],
        )

        ret = retreival.add_solution(sol_data)
        if ret != 0:
            added += 1

    print(f'Added {added}/len({r_solutions}) to database.')
    return 0


if __name__ == '__main__':

    raise SystemExit(_main())
