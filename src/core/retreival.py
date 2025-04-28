from dataclasses import asdict
from dataclasses import dataclass
from typing import Literal

import numpy as np
import psycopg
from agents.pre_processing_agent import PreProcessingAgent
from core.state import MainState
from loguru import logger
from openai import OpenAI
from utils.util_types import Puzzle


DEFAULT_WEIGHTS = {
    'full_description': 0.1,
    'problem_statement': 0.3,
    'underlying_concepts': 0.4,
    'keywords': 0.2,
}


@dataclass
class PuzzleData:
    # Note: for now parts are not used, because these required solving the
    # parts1 to be solved first
    year: int
    day: int
    full_description: str
    problem_statement: str
    keywords: list[str]
    underlying_concepts: list[str]


@dataclass
class SolutionData:
    code: str
    author: str
    source: Literal['github', 'reddit']
    puzzle_day: int
    puzzle_year: int


class PuzzleRetreival:

    def __init__(
        self,
        connection_string: str,
        openai_key: str,
        *,  # named arguments only
        pre_processing_agent: PreProcessingAgent | None = None,
        weights: dict[str, float] | None = None,
    ):

        self.connection_string = connection_string
        self.client = OpenAI(api_key=openai_key)
        self.logger = logger.bind(name='PuzzleRetreival')
        self.pre_processing_agent = pre_processing_agent
        self.weights = weights or DEFAULT_WEIGHTS

    def _get_connection(self, **kwargs):
        return psycopg.connect(self.connection_string, **kwargs)

    def init_db(
            self,
            vector_dimension: int = 1536,  # Note: default is for OpenAI small
            force: bool = False,
    ):

        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Create pgvector extension if it doesn't exist
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                if force:
                    # Drop tables if they exist and force is True
                    cur.execute("""
                    DROP TABLE IF EXISTS solutions CASCADE;
                    DROP TABLE IF EXISTS puzzles CASCADE;
                    """)

                # Check if tables already exist
                cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'puzzles'
                );
                """)

                # TODO: Check when fetchone returns None
                # (e.g. when the table doesn't exist, async?)
                puzzles_exists = cur.fetchone()
                if puzzles_exists is not None:
                    puzzles_exists = puzzles_exists[0]

                if not puzzles_exists:
                    # Create puzzles table
                    cur.execute(
                        """
                    CREATE TABLE puzzles (
                      id SERIAL PRIMARY KEY,
                      year INT NOT NULL,
                      day INT NOT NULL,
                      full_description TEXT,
                      problem_statement TEXT,
                      keywords TEXT,
                      underlying_concepts TEXT,
                      embedding VECTOR({vector_dimension}),
                      UNIQUE(year, day)
                    );
                    """, (vector_dimension,),
                    )

                    # Create index on embedding
                    cur.execute("""
                    CREATE INDEX idx_embedding ON puzzles
                    USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
                    """)
                    self.logger.info('Created puzzles table and index.')

                # Check if solutions table exists
                cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'solutions'
                );
                """)

                # TODO: Check when fetchone returns None (see above)
                solutions_exists = cur.fetchone()
                if solutions_exists is not None:
                    solutions_exists = solutions_exists[0]

                if not solutions_exists:
                    # Create solutions table
                    cur.execute("""
                    CREATE TABLE solutions (
                      id SERIAL PRIMARY KEY,
                      puzzle_id INT NOT NULL,
                      code TEXT NOT NULL,
                      author VARCHAR(255),
                      source VARCHAR(255),
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      FOREIGN KEY (puzzle_id) REFERENCES puzzles(id)
                        ON DELETE CASCADE
                    );
                    """)
                    # Create index on puzzle_id
                    cur.execute("""
                    CREATE INDEX idx_solutions_puzzle_id ON
                        solutions(puzzle_id);
                    """)
                    self.logger.info('Created solutions table and index.')

                conn.commit()
                self.logger.info('Database initialization complete.')

    def _create_embedding(self, text: str) -> list[float]:
        """
        Create an embedding for the given text using OpenAI's API.

        Args:
            text (str): The text to create an embedding for.

        Returns:
            list[float]: The embedding vector.
        """

        self.logger.trace(f'Creating embedding for {text=}')

        response = self.client.embeddings.create(
            input=text,
            model='text-embedding-3-small',
        )

        return response.data[0].embedding

    def _compute_weighted_embedding(
        self,
        puzzle: PuzzleData,
    ) -> list[float]:
        """
        Compute a weighted composite embedding for the puzzle.

        Args:
            puzzle (PuzzleData): The puzzle data.

        Returns:
            list[float]: The composite embedding.
        """

        puzzle_data = asdict(puzzle)
        # THis assumes that all the fields have a weight
        # if they need to be included in the compsite embedding
        embeddings = {}
        for field in self.weights:
            embeddings[field] = np.array(
                self._create_embedding(puzzle_data[field]),
            )

        # Calculate the composite embedding
        composite_embedding = np.zeros_like(list(embeddings.values())[0])
        for field, weight in self.weights.items():
            weighted_embedding = weight * embeddings[field]
            composite_embedding += weighted_embedding

        # Normalize the embedding
        norm = np.linalg.norm(composite_embedding)
        if norm > 0:
            composite_embedding = composite_embedding / norm

        return composite_embedding.tolist()

    def _state_to_puzzle_data(self, state: MainState) -> PuzzleData:
        """
        Convert the state to a PuzzleData object.
        """

        return PuzzleData(
            year=state.puzzle.year,
            day=state.puzzle.day,
            full_description=state.puzzle.description,
            problem_statement=state.problem_statement or '',
            keywords=state.keywords,
            underlying_concepts=state.underlying_concepts,
        )

    def add_puzzle_from_state(self, state: MainState) -> int:
        """
        Add a puzzle from the state to the database.

        Args:
            state (MainState): The state containing the puzzle.

        Returns:
            int: The ID of the added puzzle.
        """

        # TODO: Should we check here if the puzzle exists in the DB?

        # Create the composite embedding
        puzzle_data = self._state_to_puzzle_data(state)
        embedding = self._compute_weighted_embedding(
            puzzle_data,
        )

        # Add the puzzle to the Database
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                query = """
                INSERT INTO puzzles (
                    year, day, full_description, problem_statement,
                    keywords, underlying_concepts, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """

                self.logger.debug(f'Executing query: {query}')

                cur.execute(
                    query, (
                        puzzle_data.year,
                        puzzle_data.day,
                        puzzle_data.full_description,
                        puzzle_data.problem_statement,
                        puzzle_data.keywords,
                        puzzle_data.underlying_concepts,
                        embedding,
                    ),
                )

                puzzle_id = cur.fetchone()
                if puzzle_id is not None:
                    puzzle_id = puzzle_id[0]
                    self.logger.info(
                        f'Puzzle {puzzle_data.year}-{puzzle_data.day} '
                        f'added with ID {puzzle_id}.',
                    )
                    conn.commit()
                    return puzzle_id

                # TODO: Raise here?
                self.logger.error(
                    f'Failed to add puzzle to the database. {puzzle_id=}',
                )
                return 0

    def add_puzzle(self, puzzle: Puzzle) -> int:
        """
        Add a puzzle to the database.

        Note: this method requires a pre-processing agent to be available.

        Args:
            puzzle (Puzzle): The puzzle to add.

        Returns:
            int: The ID of the added puzzle.
        """

        # Check for pre-processing agent
        assert self.pre_processing_agent is not None, (
            'Pre-processing agent is not available.'
        )

        # Check if the puzzle already exists in the DB
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                SELECT id FROM puzzles
                WHERE year = %s AND day = %s;
                """, (puzzle.year, puzzle.day),
                )
                exesting_puzzle = cur.fetchone()
                if exesting_puzzle:
                    self.logger.info(
                        (
                            f'Puzzle {puzzle.year}-{puzzle.day} '
                            'already exists.'
                        ),
                    )
                    return exesting_puzzle[0]

        # Preprocess the puzzle
        state = MainState(puzzle=puzzle)
        state = self.pre_processing_agent.process(state)

        return self.add_puzzle_from_state(state)

    def add_solution(self, solution: SolutionData) -> int:
        """
        Add a solution to the database.

        Args:
            solution (SolutionData): The solution to add.

        Returns:
            int: The ID of the added solution.
        """

        # Check that the puzzle exists
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                SELECT id FROM puzzles
                WHERE year = %s AND day = %s;
                """, (solution.puzzle_year, solution.puzzle_day),
                )
                puzzle_id = cur.fetchone()
                if puzzle_id is None:
                    self.logger.error(
                        (
                            f'Puzzle {solution.puzzle_year}-'
                            f'{solution.puzzle_day} does not exist.'
                        ),
                    )
                    # TODO: Raise?
                    return 0

        # Check that the solution exists
        # TODO: Is this the best way to check that a soltuion doesn't exist?
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                SELECT id FROM solutions
                WHERE puzzle_id = %s AND author = %s;
                """, (puzzle_id, solution.author),
                )
                existing_solution = cur.fetchone()
                if existing_solution:
                    self.logger.info(
                        (
                            f'Solution by {solution.author} for '
                            f'puzzle {solution.puzzle_year}-'
                            f'{solution.puzzle_day} '
                            'already exists.'
                        ),
                    )
                    return existing_solution[0]

        # Add the solution to the Database
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                INSERT INTO solutions (
                    puzzle_id, code, author, source
                ) VALUES (%s, %s, %s, %s)
                RETURNING id;
                """, (
                        puzzle_id,
                        solution.code,
                        solution.author,
                        solution.source,
                    ),
                )
                solution_id = cur.fetchone()
                if solution_id is not None:
                    solution_id = solution_id[0]
                    self.logger.info(
                        f'Solution added with ID {solution_id}.',
                    )
                    conn.commit()
                    return solution_id

                return 0

    def get_similar_puzzles_from_state(
        self,
        state: MainState,
        limit: int = 3,
    ) -> list[PuzzleData]:

        # Create PuzzleData
        puzzle_data = self._state_to_puzzle_data(state)
        # Create embedding
        embedding = self._compute_weighted_embedding(puzzle_data)

        # Query the DB for similar puzzles
        with self._get_connection() as conn:
            with conn.cursor() as cur:

                query = """
                SELECT id, year, day, full_description, problem_statement,
                        keywords, underlying_concepts,
                        embedding <-> %s::vector AS distance
                FROM puzzles
                ORDER BY distance
                LIMIT %s;
                """

                cur.execute(query, (embedding, limit))
                results = cur.fetchall()

                return [
                    PuzzleData(
                        year=result[1],
                        day=result[2],
                        full_description=result[3],
                        problem_statement=result[4],
                        keywords=result[5],
                        underlying_concepts=result[6],
                    ) for result in results
                ]

    def get_similar_puzzles(
        self,
        puzzle: Puzzle,
        limit: int = 3,
    ) -> list[PuzzleData]:

        # Create state object from puzzle
        state = MainState(puzzle=puzzle)

        # Pre-process the puzzel (extract keywords, etc.)
        assert self.pre_processing_agent is not None, (
            'Pre-processing agent is not available.'
        )

        state = self.pre_processing_agent.process(state)

        return self.get_similar_puzzles_from_state(state, limit=limit)

    def get_solutions(
        self,
        puzzle_year: int,
        puzzle_day: int,
        limit: int = 3,
    ) -> list[SolutionData]:

        with self._get_connection() as conn:
            with conn.cursor() as cur:

                cur.execute(
                    """
                            SELECT code, author, source
                            FROM solutions
                            WHERE puzzle_id = (
                                SELECT id
                                FROM puzzles p
                                WHERE p."day" = %s and p."year" = %s
                            )
                            LIMIT %s
                            """, (puzzle_day, puzzle_year, limit),
                )

                results = cur.fetchall()

                return [
                    SolutionData(
                        code=result[0],
                        author=result[1],
                        source=result[2],
                        puzzle_day=puzzle_day,
                        puzzle_year=puzzle_year,
                    ) for result in results
                ]
