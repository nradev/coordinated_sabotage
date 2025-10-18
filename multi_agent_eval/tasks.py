"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset
from inspect_ai.model import GenerateConfig

from multi_agent_eval.environment.agents import agent_collection_solver
from multi_agent_eval.samples import unique_digits, webserver

from multi_agent_eval.environment.scorer import multi_agent_scorer


@task
def multi_agent_file_modification(max_messages: int = 100, temperature: float = 0.7) -> Task:
    """
    Create a multi-agent file modification evaluation task.

    Args:
        max_messages: Maximum messages per conversation
        temperature: Temperature for generation
    """

    dataset = MemoryDataset([webserver.create_sample()])
    # dataset = MemoryDataset([unique_digits.create_sample()])

    return Task(
        dataset=dataset,
        solver=agent_collection_solver(),
        scorer=multi_agent_scorer(),
        config=GenerateConfig(temperature=temperature, max_tokens=2000),
        sandbox="docker",
        message_limit=max_messages,
    )
