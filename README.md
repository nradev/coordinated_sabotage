# Coordinated Sabotage Test

## Setup

### 1. Install uv

This project uses [uv](https://docs.astral.sh/uv/) for dependency management. Install uv if you haven't already:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install Dependencies

Install the project and all dependencies with the `dev` group:

```bash
uv sync --dev
```

This creates a virtual environment and installs all required dependencies including development tools.

### 3. Install Pre-commit Hooks

Set up pre-commit hooks for code quality:

```bash
uv run pre-commit install
```

The pre-commit hooks will automatically run ruff formatting on Python files before each commit.

### 4. Set API Keys

Configure your API keys for the evaluation:

```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

## Running the Project

Run an evaluation:

```bash
uv run inspect eval multi_agent_eval/test_eval.py --model anthropic/claude-3-opus
```

Evaluation results will be saved in the `logs/` directory.

## Development

### Code Quality

Run ruff manually for code formatting and linting:

```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Fix issues automatically
uv run ruff check --fix .
```

### Adding Dependencies

```bash
# Add runtime dependency
uv add package-name

# Add development dependency
uv add --dev package-name
```

## Using Inspect fork with Timeline log viewer

```bash
# Clone this inspect fork
git clone https://github.com/nradev/inspect_ai.git
cd inspect_ai

# Checkout the multi_agent_timeline branch
git checkout multi_agent_timeline

# Activate the environment and start the log viewer in a specific directory
source .venv/bin/activate && inspect view --log-dir ~/code/coordinated_sabotage_test/logs
```

## Tracking Evaluations with Weights & Biases

The [`inspect-wandb` tutorial](https://inspect-wandb.readthedocs.io/en/latest/tutorial.html) walks through connecting Inspect evaluations to Weights & Biases for richer experiment tracking. 

```bash
# set your WANDB_API_KEY
export WANDB_API_KEY="your-api-key"

# setup wand
wandb init
wandb login

# run the evaluation; this will automatically log your run
uv run inspect eval multi_agent_eval/test_eval.py
```

Refer to the tutorial for advanced configuration options such as grouping runs, attaching custom metadata, or streaming live metrics.

