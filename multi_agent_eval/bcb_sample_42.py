"""
Unique Digits
"""

from inspect_ai.dataset import Sample

from agents import AgentConfig

import json

with open("../bcb/samples_files.json", "r", encoding="utf-8") as f:
    samples = json.load(f)


def create_sample() -> Sample:
    """Create dataset with multi-agent file modification tasks."""
    files_content = samples["sample_42"]

    agents_config = [
        AgentConfig(
            id="agent_0",
            read_access="ALL",
            write_access=["pca_transformation.py"],
            agent_specific_message="""You are responsible for implementing pca_transformation.py. 
Work with other agents to ensure the complete system functions correctly.""",
            keep_common_message=True,
        ),
        AgentConfig(
            id="agent_1",
            read_access="ALL",
            write_access=["dataframe_creation.py"],
            agent_specific_message="""You are responsible for implementing dataframe_creation.py.
Work with other agents to ensure the complete system functions correctly.""",
            keep_common_message=True,
        ),
        AgentConfig(
            id="agent_2",
            read_access="ALL",
            write_access=["variance_plotting.py"],
            agent_specific_message="""You are responsible for implementing variance_plotting.py.
Work with other agents to ensure the complete system functions correctly.""",
            keep_common_message=True,
        ),
    ]
    common_message = f"""Your task is to implement the functions used by task_func in the task.py file 
such that task_func performs according to the specification in its docstring.

Ensure all changes are consistent and the tests pass after implementation."""

    return Sample(
        input=common_message,
        files=files_content,
        metadata={
            "agents_config": agents_config,
            "task_type": "implementation",
            "difficulty": "easy",
        },
    )
