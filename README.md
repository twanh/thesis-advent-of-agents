# Advent of Agents: A Multi-Agent Approach to Solving Advent of Code Puzzles

## Overview

This project implements a modular multi-agent system to automatically solve Advent of Code puzzles. It uses a pipeline of agents—PreProcessing, Retrieval, Planning, and Coding—coordinated by an orchestrator. Each agent leverages large language models (e.g., OpenAI, Gemini, Deepseek) and, in the case of RetrievalAgent, a PostgreSQL database with the pgvector extension to fetch and reuse past solutions.

## Architecture

Simple ASCII diagram (excluding MockAgents):

```
     +----------------+
     |  Puzzle Input  |
     +----------------+
             |
             v
  +-----------------------+
  | PreProcessingAgent    |
  +-----------------------+
             |
             v
  +-----------------------+
  | RetrievalAgent        |
  +-----------------------+
             |
             v
  +-----------------------+
  | PlanningAgent         |
  +-----------------------+
             |
             v
  +-----------------------+
  | CodingAgent           |
  +-----------------------+
             |
             v
  +-----------------------+
  | DebuggingAgent        |
  +-----------------------+
             |
             v
     +----------------+
     |  Solution      |
     +----------------+
```

All agents are managed by the `Orchestrator` in `src/core/orchestrator.py`.

## Installation

**Prerequisites**:
- Python 3.10 or higher
- PostgreSQL database with the `pgvector` extension
- API keys for the LLMs you plan to use (e.g., OpenAI, Gemini, Deepseek)

**Steps**:

```bash
# Clone the repository
git clone git@github.com:twanh/thesis-advent-of-agents
cd thesis-advent-of-agents

# (Optional) Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables (e.g., in a .env file)
export OPENAI_API_KEY=your_openai_api_key
export GEMINI_API_KEY=your_gemini_api_key
export DEEPSEEK_API_KEY=your_deepseek_api_key
export DB_CONNECTION_STRING="postgresql://user:password@host:port/dbname"
```

### Database Initialization

Initialize the puzzles and solutions tables:

```bash
python scripts/add_puzzles.py path/to/puzzles_dir $DB_CONNECTION_STRING
```

## Usage

Solve a puzzle by providing the description and input files:

```bash
python src/main.py \
  --puzzle path/to/puzzle.txt \
  --puzzle-input path/to/input.txt \
  --year 2024 \
  --day 1 \
  --default-model openai-gpt-4 \
  --log-level INFO
```

**Options**:
- `--expected-output`: expected solution (for verification)
- `--disable-agents`: disable specified agents (e.g., `--disable-agents retrieval debugging`)
- `--preprocess-model`, `--retreival-model`, `--planning-model`, `--coding-model`, `--debugging-model`: override default model per agent
- `--log-level`: set logging level (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Adding Solutions

Import solutions (e.g., from Reddit) into the database:

```bash
python scripts/add_solutions_reddit.py path/to/solutions.json $DB_CONNECTION_STRING
```
