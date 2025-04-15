from dataclasses import dataclass

import psycopg
from loguru import logger
from openai import OpenAI


@dataclass
class PuzzleData:
    year: int
    day: int
    full_description: str
    problem_statement: str
    keywords: list[str]
    underlying_concepts: list[str]


class PuzzleRetreival:

    def __init__(self, connection_string: str, openai_key: str):

        self.connection_string = connection_string
        self.client = OpenAI(api_key=openai_key)
        self.logger = logger.bind(name='PuzzleRetreival')

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
