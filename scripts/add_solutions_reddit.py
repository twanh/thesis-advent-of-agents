import argparse
import json
import os
import sys

import dotenv
import loguru
from tqdm import tqdm


PROJECT_ROOT = os.path.join(
    os.path.dirname(
        os.path.abspath(__file__),
    ), '../src/',
)
sys.path.append(PROJECT_ROOT)

from core.retreival import PuzzleRetreival  # NOQA
from core.retreival import SolutionData  # NOQA


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

    parser.add_argument(
        '-l', '--log-level',
        type=str,
        default='ERROR',
        help='Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)',
    )

    parser.add_argument(
        '--language',
        type=str,
        help='Only add solutions with the given langauge to the database.',
    )
    args = parser.parse_args()

    loguru.logger.remove()
    loguru.logger.add(sys.stderr, level=args.log_level)

    dotenv.load_dotenv()

    retreival = PuzzleRetreival(
        connection_string=args.db,
        openai_key=os.getenv('OPENAI_API_KEY'),
    )

    retreival.init_db()

    with open(args.json_file, 'r') as f:
        solutions = json.load(f)

    print(f'Found {len(solutions)}')

    added = 0
    skipped = 0
    for solution in tqdm(solutions):

        # If language is specified only add solutions with
        # the correct language
        if args.language:
            if solution['language'].lower() != args.language.lower():
                skipped += 1
                continue

        sol_data = SolutionData(
            code=solution['code'],
            author=solution['author'],
            source='reddit',
            puzzle_day=solution['puzzle_day'],
            puzzle_year=solution['puzzle_year'],
        )

        ret = retreival.add_solution(sol_data)
        if ret != 0:
            added += 1

    print(f'Added {added}/{len(solutions)} to database.')
    print(f'Skipped {skipped} solutions (did not meet language requirement)')
    print(
        f'Missed {len(solutions)-(added+skipped)}\
          solutions due to other reasons',
    )

    return 0


if __name__ == '__main__':

    raise SystemExit(_main())
