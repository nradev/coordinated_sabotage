from collections.abc import Callable
from dataclasses import dataclass

from inspect_ai.dataset import Dataset, MemoryDataset, Sample


@dataclass(frozen=True)
class RegisteredSample:
    name: str
    factory: Callable[[], Sample]
    description: str

    def as_dataset(self) -> Dataset:
        return MemoryDataset([self.factory()])


SAMPLES: dict[str, RegisteredSample] = {}


def register_sample(name: str, *, description: str) -> Callable[[Callable[[], Sample]], Callable[[], Sample]]:
    """Register a sample factory under ``name`` using a decorator."""

    def decorator(factory: Callable[[], Sample]) -> Callable[[], Sample]:
        if name in SAMPLES:
            raise ValueError(f"Sample '{name}' already registered")
        SAMPLES[name] = RegisteredSample(name=name, factory=factory, description=description)
        return factory

    return decorator


def get_sample(name: str) -> RegisteredSample:
    """Return a sample instance registered under ``name``."""
    try:
        registered = SAMPLES[name]
    except KeyError as exc:
        available = ", ".join(sorted(SAMPLES))
        raise KeyError(f"Unknown sample '{name}'. Available samples: {available}") from exc
    return registered


def list_samples() -> list[RegisteredSample]:
    """Expose registered samples for discovery."""
    return list(SAMPLES.values())
