from collections.abc import Callable
from dataclasses import dataclass

from inspect_ai.dataset import Dataset, MemoryDataset

from multi_agent_eval.samples import append_log_db, unique_digits


@dataclass(frozen=True)
class RegisteredDataset:
    name: str
    factory: Callable[[], Dataset]
    description: str


def _memory_dataset_from_sample(sample_factory: Callable[[], object]) -> Dataset:
    """Wrap a single sample-producing callable in a MemoryDataset."""
    return MemoryDataset([sample_factory()])


DATASETS: dict[str, RegisteredDataset] = {
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


def get_dataset(name: str) -> Dataset:
    """Return a dataset instance registered under ``name``."""
    try:
        registered = DATASETS[name]
    except KeyError as exc:
        available = ", ".join(sorted(DATASETS))
        raise KeyError(f"Unknown dataset '{name}'. Available datasets: {available}") from exc
    return registered.factory()


def list_datasets() -> list[RegisteredDataset]:
    """Expose registered datasets for discovery."""
    return list(DATASETS.values())
