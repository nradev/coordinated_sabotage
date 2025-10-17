"""Typer CLI for running Inspect AI evaluations with configurable tasks."""

from __future__ import annotations

import typer
from inspect_ai import eval as run_eval
from typing_extensions import Annotated

from multi_agent_eval.agents import list_solvers
from multi_agent_eval.samples.registry import list_samples
from multi_agent_eval.tasks import (
    multi_agent_file_modification,
)

app = typer.Typer(
    help="Run multi-agent Inspect AI evaluations with configurable datasets and solvers.",
)


def _format_registry_entries(entries) -> str:
    # TODO: "\n" is not printed in help
    return "\n".join(f"- {entry.name}: {entry.description}" for entry in entries)


@app.command()
def run(
    sample: Annotated[
        str,
        typer.Option(
            "--sample",
            help="Sample to evaluate. Available options:\n" + _format_registry_entries(list_samples()),
        ),
    ] = "unique_digits",
    solver: Annotated[
        str,
        typer.Option(
            "--solver",
            help="Solver to use. Available options:\n" + _format_registry_entries(list_solvers()),
        ),
    ] = "multi",
    temperature: Annotated[
        float,
        typer.Option("--temperature", "-t", help="Model temperature used during generation."),
    ] = 0.7,
    max_messages: Annotated[
        int,
        typer.Option("--max-messages", "-m", help="Message limit enforced by the solver."),
    ] = 100,
    model: Annotated[
        str,
        typer.Option("--model", help="Model identifier to run the evaluation with."),
    ] = "openai/gpt-4o-mini",
) -> None:
    """
    Execute an Inspect AI evaluation with the configured dataset and solver.
    """

    task = multi_agent_file_modification(
        sample=sample,
        solver=solver,
        temperature=temperature,
        max_messages=max_messages,
    )

    run_eval(tasks=[task], model=model)


if __name__ == "__main__":
    app()
