"""
Utilities for constructing Inspect AI tasks used in the multi-agent evaluation.

The module now exposes a task builder that allows callers to inject both the
dataset and solver implementations. Convenience registries are provided so
command-line tooling (and downstream users) can select from the built-in
options, but the builder works with any compatible dataset or solver.
"""

from __future__ import annotations

from typing import Callable

from inspect_ai import Task, task
from inspect_ai.dataset import Dataset
from inspect_ai.model import GenerateConfig
from inspect_ai.solver import Solver

from multi_agent_eval.agents import get_solver
from multi_agent_eval.samples import get_dataset
from multi_agent_eval.scorer import multi_agent_scorer

DatasetFactory = Callable[[], Dataset]
SolverFactory = Callable[[int], Solver]

# TODO: clean-up: move dataset and solver registry to the dedicated module and add a register-decorator


@task
def multi_agent_file_modification(
    *,
    dataset: str = "unique_digits",
    solver: str = "multi",
    max_messages: int = 100,
    temperature: float = 0.7,
    max_tokens: int = 2000,
    sandbox: str = "docker",
) -> Task:
    """
    Default Inspect AI task used by the evaluation harness.

    Callers can override the dataset or solver by specifying the corresponding registry keys.
    """

    dataset = get_dataset(dataset)
    solver = get_solver(solver, max_messages=max_messages)

    return Task(
        dataset=dataset,
        solver=solver,
        scorer=multi_agent_scorer(),
        config=GenerateConfig(temperature=temperature, max_tokens=max_tokens),
        sandbox=sandbox,
        message_limit=max_messages,
    )
