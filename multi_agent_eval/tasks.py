"""
Utilities for constructing Inspect AI tasks used in the multi-agent evaluation.

The module now exposes a task builder that allows callers to inject both the
dataset and solver implementations. Convenience registries are provided so
command-line tooling (and downstream users) can select from the built-in
options, but the builder works with any compatible dataset or solver.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List

from inspect_ai import Task, task
from inspect_ai.agent import as_solver
from inspect_ai.dataset import Dataset, MemoryDataset
from inspect_ai.model import GenerateConfig
from inspect_ai.solver import Solver
from inspect_ai.util import message_limit

from .agents import agent_collection_solver, forgetful_agent
from .samples import unique_digits, webserver, append_log_db
from .scorer import multi_agent_scorer

DatasetFactory = Callable[[], Dataset]
SolverFactory = Callable[[int], Solver]

# TODO: clean-up: move dataset and solver registry to the dedicated module and add a register-decorator


@dataclass(frozen=True)
class RegisteredDataset:
    name: str
    factory: Callable[[], Dataset]
    description: str


@dataclass(frozen=True)
class RegisteredSolver:
    name: str
    factory: Callable[[int], Solver]
    description: str


def _memory_dataset_from_sample(sample_factory: Callable[[], object]) -> Dataset:
    """Wrap a single sample-producing callable in a MemoryDataset."""
    return MemoryDataset([sample_factory()])


DATASETS: Dict[str, RegisteredDataset] = {
    "unique_digits": RegisteredDataset(
        name="unique_digits",
        factory=lambda: _memory_dataset_from_sample(unique_digits.create_sample),
        description="Unique digits multi-file refactoring exercise.",
    ),
    "append_log_db": RegisteredDataset(
        name="append_log_db",
        factory=lambda: _memory_dataset_from_sample(append_log_db.create_sample),
        description="Append-only log database compaction exercise.",
    ),
}


def _build_forgetful_solver(max_messages: int) -> Solver:
    agent = forgetful_agent(include_test_results=True, include_tests=False)
    return as_solver(agent, limits=[message_limit(max_messages)])


def _build_agent_collection_solver(max_messages: int) -> Solver:
    # The agent collection solver already returns a Solver via the decorator.
    return agent_collection_solver()


SOLVERS: Dict[str, RegisteredSolver] = {
    "forgetful": RegisteredSolver(
        name="forgetful",
        factory=_build_forgetful_solver,
        description="Single forgetful agent baseline.",
    ),
    "multi": RegisteredSolver(
        name="multi",
        factory=_build_agent_collection_solver,
        description="Multi-agent collaborative solver.",
    ),
}


def get_dataset(name: str) -> Dataset:
    """Return a dataset instance registered under ``name``."""
    try:
        registered = DATASETS[name]
    except KeyError as exc:
        available = ", ".join(sorted(DATASETS))
        raise KeyError(f"Unknown dataset '{name}'. Available datasets: {available}") from exc
    return registered.factory()


def get_solver(name: str, *, max_messages: int) -> Solver:
    """Return a solver instance registered under ``name``."""
    try:
        registered = SOLVERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(SOLVERS))
        raise KeyError(f"Unknown solver '{name}'. Available solvers: {available}") from exc
    return registered.factory(max_messages)


def list_datasets() -> List[RegisteredDataset]:
    """Expose registered datasets for discovery."""
    return list(DATASETS.values())


def list_solvers() -> List[RegisteredSolver]:
    """Expose registered solvers for discovery."""
    return list(SOLVERS.values())


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
