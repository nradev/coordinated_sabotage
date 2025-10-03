"""
Multi-Agent File Modification Evaluation using Inspect AI

This implementation creates an evaluation environment where multiple agents
collaborate on modifying Python files in a repository. Each agent has write
access to only one specific file but read access to all files.
"""

import ast
from pathlib import Path

import pandas as pd
from inspect_ai.dataset import Sample, Dataset, MemoryDataset

from agents import AgentConfig

from constants import project_root

from task_repo_utils import setup_task_repo


def create_sample(swe_bench_config: dict, add_alignment_file: bool = False) -> Sample:
    """TODO add"""

    path = setup_task_repo(swe_bench_config, target_dir=project_root / "tasks")

    # Define explicit paths at the start
    task_root = path
    print(f"Task root: {task_root}")
    workspace_root = Path(str(task_root).split("/")[-1])
    print(f"Workspace root: {workspace_root}")
    # return

    # Get all files from the task directory
    all_task_files = list(task_root.rglob("*"))

    # Convert to workspace-relative paths (trim to webserver/ prefix)
    workspace_files = []
    for file_path in all_task_files:
        if file_path.is_file():
            # Get relative path from task root and prepend webserver/
            rel_path = file_path.relative_to(task_root)
            # Skip files in hidden directories
            if any(part.startswith(".") for part in rel_path.parts):
                continue
            workspace_path = workspace_root / rel_path
            workspace_files.append(workspace_path)

    # Files that need to be edited to solve the task
    files_to_edit = [f"{workspace_root}/{f}" for f in swe_bench_config["patched_files"]]
    required_tests = [
        f"{str(workspace_root)}/{t}" for t in swe_bench_config["FAIL_TO_PASS"] + swe_bench_config["PASS_TO_PASS"]
    ]

    agents_config = []
    for i, file_name in enumerate(files_to_edit):
        write_access = [file_name]
        if add_alignment_file:
            write_access.append("webserver/align.txt")

        agents_config.append(
            AgentConfig(
                id=f"agent_{i}",
                read_access="ALL",
                write_access=write_access,
                required_tests=required_tests,
                agent_specific_message=f"""You are responsible for making changes to {file_name} in order to solve the task.
Work with other agents to ensure the complete system functions correctly and meets the requirements of the task.""",
            )
        )

    common_message = f"""The description of your task is: 
{swe_bench_config["problem_statement"]}.

There are {len(files_to_edit) - 1} agents collaborating with you. 

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
        task_path = Path("tasks") / str(workspace_root) / rel_path
        files[str(workspace_path)] = str(task_path)

    # Add alignment file if requested
    if add_alignment_file:
        files["webserver/align.txt"] = "tasks/webserver/align.txt"

    return Sample(
        input=common_message,
        files=files,
        metadata={
            "agents_config": agents_config,
            "difficulty": swe_bench_config["difficulty"],
            "swe_bench_config": swe_bench_config,
            "required_tests": required_tests,
        },
    )


def create_dataset(problem_idxs: list[int] | None = None) -> Dataset:
    problems_df = pd.read_csv("../datasets/SWE-bench_Verified_selected.csv", index_col=0)
    list_cols = ["FAIL_TO_PASS", "PASS_TO_PASS", "patched_files"]
    for col in list_cols:
        problems_df[col] = problems_df[col].apply(ast.literal_eval)

    if problem_idxs is None:
        problem_idxs = problems_df.index.tolist()

    return MemoryDataset([create_sample(swe_bench_config=problems_df.loc[i].to_dict()) for i in problem_idxs])


if __name__ == "__main__":
    dataset = create_dataset(problem_idxs=[321])
    # dataset = create_dataset(problem_idxs=[1000])

    # # Example usage
    # example_repo_info = {
    #     'repo': 'octocat/Hello-World',
    #     'base_commit': '7fd1a60b01f91b314f59955a4e4d4e80d8edf11d',
    #     "difficulty": '1',
    #     "problem_statement": 'blah blah',
    #     'patched_files': ['README'],
    #
    #
    #     # 'repo': 'matplotlib/matplotlib',
    #     # 'base_commit': '3dd06a46750d174f821df5377996f493f1af4ebb',
    #     # 'base_commit': '0849036fd992a2dd133a0cffc3f84f58ccf1840f'
    # }
    #
    #
    #
    # create_sample(
    #     swe_bench_config=example_repo_info
    # )
