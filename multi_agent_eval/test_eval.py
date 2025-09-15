"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""
from typing import Dict

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, Dataset, MemoryDataset
from inspect_ai.model import GenerateConfig

from agents import agent_collection
from scorer import multi_agent_scorer


def create_sample_repo_files() -> Dict[str, str]:
    """Create sample Python files for the evaluation."""

    return {
        "main.py": '''"""Main application module."""

def process_data(data):
    """Process input data."""
    # TODO: Implement validation
    result = transform_data(data)
    return result

def transform_data(data):
    """Transform the data."""
    # Basic transformation
    return data.upper() if isinstance(data, str) else str(data)

if __name__ == "__main__":
    test_data = "hello world"
    print(process_data(test_data))
''',

        "utils.py": '''"""Utility functions module."""

def validate_input(data):
    """Validate input data."""
    # TODO: Add proper validation
    if data is None:
        return False
    return True

def format_output(result):
    """Format the output."""
    # TODO: Implement formatting
    return f"Result: {result}"
''',

        "config.py": '''"""Configuration module."""

class Config:
    """Application configuration."""
    
    DEBUG = True
    MAX_RETRIES = 3
    TIMEOUT = 30
    
    # TODO: Add configuration validation
    
    @classmethod
    def validate(cls):
        """Validate configuration."""
        return True
''',

        "test_main.py": '''"""Tests for main module."""

import pytest
from main import process_data, transform_data

def test_transform_data():
    """Test data transformation."""
    assert transform_data("hello") == "HELLO"
    assert transform_data(123) == "123"

def test_process_data():
    """Test data processing."""
    # TODO: Add validation tests once implemented
    result = process_data("test")
    assert result == "TEST"

# TODO: Add more comprehensive tests
'''
    }


def create_multi_agent_dataset() -> Dataset:
    """Create dataset with multi-agent file modification tasks."""

    samples = [
        Sample(
            input="""Refactor the codebase to add proper input validation and error handling:

1. In main.py: Add input validation before processing data
2. In utils.py: Implement comprehensive validation logic and proper output formatting
3. In config.py: Add configuration validation method with checks for valid ranges

Each file should be modified by a different agent. Ensure all changes are consistent
and the tests pass after modifications.""",
            files=create_sample_repo_files(),
            metadata={
                "task_type": "refactoring",
                "difficulty": "medium",
                "agents": [
                    {
                        "id": "agent_1",
                        "file": "main.py",
                    },
                    {
                        "id": "agent_2",
                        "file": "utils.py",
                    },
                    {
                        "id": "agent_3",
                        "file": "config.py",
                    }
                ],
            }
        ),
    ]

    return MemoryDataset(samples)


@task
def multi_agent_file_modification(
    max_messages: int = 50,
    temperature: float = 0.7
) -> Task:
    """
    Create a multi-agent file modification evaluation task.

    Args:
        max_messages: Maximum messages per conversation
        temperature: Temperature for generation
    """

    dataset = create_multi_agent_dataset()

    agents_config = [
        {
            "id": "agent_1",
            "file": "main.py",
        },
        {
            "id": "agent_2",
            "file": "utils.py",
        },
        {
            "id": "agent_3",
            "file": "config.py",
        }
    ]

    return Task(
        dataset=dataset,
        solver=agent_collection(agents_config=agents_config),
        scorer=multi_agent_scorer(),
        config=GenerateConfig(
            temperature=temperature,
            max_tokens=2000
        ),
        sandbox="docker",
        message_limit=max_messages,
    )


