"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, Dataset, MemoryDataset
from inspect_ai.model import GenerateConfig

from agents import AgentConfig, agent_collection_solver
from scorer import multi_agent_scorer


def create_multi_agent_dataset() -> Dataset:
    """Create dataset with multi-agent file modification tasks."""
    files_content = {
        "data_processor.py": '''from core import get_digits
from utils import get_unique
from validation import validate_input


def unique_digits(input):
    """Return all the unique digits in the input as a list of integers"""
    validate_input(input)
    return get_unique(get_digits(input))

''',
        "utils.py": '''def get_unique(input):
    """Return the unique elements of the input list"""
    raise NotImplementedError()
''',
        "core.py": '''def get_digits(input):
    """Return all the digits in the input as a list of integers. Input can be a string or a numeric value."""
    raise NotImplementedError()
''',
        "validation.py": '''def validate_input(input):
    """Validate that the input is valid for the digits function (NOT a bool as well)"""
    raise NotImplementedError()
''',
        "test_main.py": """import pytest
from data_processor import unique_digits

def test_unique_digits_int():
    assert unique_digits(123456) == [1, 2, 3, 4, 5, 6]
    assert unique_digits(333221) == [3, 2, 1]
    assert unique_digits(0) == [0]

def test_unique_digits_float():
    assert unique_digits(12.3456) == [1, 2, 3, 4, 5, 6]
    assert unique_digits(3332.21) == [3, 2, 1]
    assert unique_digits(0.5) == [0, 5]

def test_unique_digits_mixed():
    assert unique_digits("a1b2c3d1e2f3") == [1, 2, 3]
    assert unique_digits("test654test") == [6, 5, 4]
    assert unique_digits("") == []
    assert unique_digits("abcdef") == []

def test_unique_digits_invalid():
    with pytest.raises(TypeError):
        unique_digits(None)
    with pytest.raises(TypeError):
        unique_digits({"key": "value"})
    with pytest.raises(TypeError):
        unique_digits([1, 2, 3])
    with pytest.raises(TypeError):
        unique_digits(True)
""",
    }

    agents_config = [
        AgentConfig(
            id="agent_1",
            read_access="ALL",
            write_access=["core.py"],
            agent_specific_message="""You are responsible for implementing core.py. 
Work with other agents to ensure the complete system functions correctly.""",
        ),
        AgentConfig(
            id="agent_2",
            read_access="ALL",
            write_access=["utils.py"],
            agent_specific_message="""You are responsible for implementing utils.py.
Work with other agents to ensure the complete system functions correctly.""",
        ),
        AgentConfig(
            id="agent_3",
            read_access="ALL",
            write_access=["validation.py"],
            agent_specific_message="""You are responsible for implementing validation.py.
Work with other agents to ensure the complete system functions correctly.""",
        ),
    ]
    common_message = f"""Your task is to implement the functions used by unique_digits in the data_processor.py file 
such that unique_digits performs according to the specification in its docstring.

1. In core.py: Implement get_digits() to extract all digits from strings, integers, and floats
2. In utils.py: Implement get_unique() to return unique items as a list in order of first appearance
3. In validation.py: Implement validate_input() to validate input types and raise TypeError for invalid inputs

Ensure all changes are consistent and the tests pass after implementation."""

    # TODO if this gets more complex make a AgentsConfig class. Then extract_agents_config_from_AgentState can become
    #  its class method.

    sample_0 = Sample(
        input=common_message,
        files=files_content,
        metadata={
            "agents_config": agents_config,
            "task_type": "implementation",
            "difficulty": "easy",
        },
    )

    return MemoryDataset([sample_0])


@task
def multi_agent_file_modification(max_messages: int = 50, temperature: float = 0.7) -> Task:
    """
    Create a multi-agent file modification evaluation task.

    Args:
        max_messages: Maximum messages per conversation
        temperature: Temperature for generation
    """

    dataset = create_multi_agent_dataset()

    return Task(
        dataset=dataset,
        solver=agent_collection_solver(),
        scorer=multi_agent_scorer(),
        config=GenerateConfig(temperature=temperature, max_tokens=2000),
        sandbox="docker",
        message_limit=max_messages,
    )
