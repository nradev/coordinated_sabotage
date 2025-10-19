"""
Utilities for constructing Inspect AI tasks used in the multi-agent evaluation.

The module now exposes a task builder that allows callers to inject both the
dataset and solver implementations. Convenience registries are provided so
command-line tooling (and downstream users) can select from the built-in
options, but the builder works with any compatible dataset or solver.
"""

from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.model import GenerateConfig
from loguru import logger

from multi_agent_eval.agents import get_solver
from multi_agent_eval.samples import get_sample
from multi_agent_eval.scorer import multi_agent_scorer

# TODO: `uv run inspect eval` does not lod run.py -> moving the log configuration there does not have an effect.
# For now I will put it here as this module is always imported.
_LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)
logger.add(_LOG_DIR / "eval_{time}.log", level="DEBUG")


@task
def multi_agent_file_modification(
    *,
    sample: str = "unique_digits",
    dataset: str | None = None,  # TODO: implement dataset support to distinguish between sample and dataset
    solver: str = "debug",
    max_messages: int = 100,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    sandbox: str = "docker",
) -> Task:
    """
    Default Inspect AI task used by the evaluation harness.

    Callers can override the dataset or solver by specifying the corresponding registry keys.
    """

    dataset = get_sample(sample).as_dataset()
    solver = get_solver(solver)

    return Task(
        dataset=dataset,
        solver=solver,
        scorer=multi_agent_scorer(),
        config=GenerateConfig(temperature=temperature, max_tokens=max_tokens),
        sandbox=sandbox,
        message_limit=max_messages,
    )
