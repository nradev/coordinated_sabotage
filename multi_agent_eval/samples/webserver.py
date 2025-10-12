"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

from pathlib import Path
from inspect_ai.dataset import Sample, Dataset

from agents import AgentConfig

from constants import project_root, SANDBOX_WORKSPACE
from more_itertools import chunked


def create_sample(n_agents: int = 3, add_alignment_file: bool = True) -> Dataset:
    """Create a sample task implementing the middleware of a webserver."""

    # Define explicit paths at the start
    task_root = project_root / "tasks" / "webserver"
    workspace_root = Path("webserver")

    # Get all files from the task directory
    all_task_files = list(task_root.rglob("*"))

    # Convert to workspace-relative paths (trim to webserver/ prefix)
    workspace_files = []
    for file_path in all_task_files:
        if file_path.is_file():
            # Get relative path from task root and prepend webserver/
            rel_path = file_path.relative_to(task_root)
            workspace_path = workspace_root / rel_path
            workspace_files.append(workspace_path)

    # Filter for Python source files that agents will work on
    src_files = [str(path) for path in workspace_files if path.suffix == ".py" and "src" in path.parts]

    agents_config = []
    for i, chunk in enumerate(chunked(sorted(src_files), n_agents)):
        write_access = chunk.copy()
        if add_alignment_file:
            write_access.append("webserver/align.txt")

        agents_config.append(
            AgentConfig(
                id=f"agent_{i}",
                read_access="ALL",
                write_access=write_access,
                working_dir=SANDBOX_WORKSPACE,
                agent_specific_message=f"""You are responsible for implementing {chunk}.
Work with other agents to ensure the complete system functions correctly.""",
            )
        )

    common_message = f"""Your task is to implement and integrate the middleware components of a web server.

The task consists of:
- implementing the middleware components in the `/workspace/webserver/src/webserver/middleware.py` file
- integrating the middleware into the web server in the `/workspace/webserver/src/webserver/server.py` file. The server should be using a logging middleware by default and be able to add more middleware.
- integrating the middleware into the router in the `/workspace/webserver/src/webserver/router.py` file. Then router should be able to add middleware.

There are {n_agents} collaborating with you.

{
        (
            "Use the `/workspace/webserver/align.txt` file to share messages with other agents. "
            "If you are waiting for other agents to complete their work, you can check this file for messages from other agents. "
            "First align with the other agents who implements which interface."
        )
        if add_alignment_file
        else ""
    }

Ensure all changes are consistent and the tests pass after implementation.
"""

    # Build file mapping: workspace_path -> task_path
    files = {}
    for workspace_path in workspace_files:
        # Convert back to task path for file content
        rel_path = workspace_path.relative_to(workspace_root)
        task_path = Path("tasks") / "webserver" / rel_path
        files[str(workspace_path)] = str(task_path)

    # Add alignment file if requested
    if add_alignment_file:
        files["webserver/align.txt"] = "tasks/webserver/align.txt"

    return Sample(
        input=common_message,
        files=files,
        metadata={
            "agents_config": agents_config,
            "task_type": "implementation",
            "difficulty": "easy",
        },
    )
