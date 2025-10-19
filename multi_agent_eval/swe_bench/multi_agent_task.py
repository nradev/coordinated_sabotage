import json
import logging
import re
import shlex
from functools import partial
from importlib.util import find_spec
from textwrap import dedent
from typing import Callable, Literal, List

import pandas as pd
from inspect_ai import Task, task
from inspect_ai.dataset import FieldSpec, hf_dataset, Sample
from inspect_ai.scorer import Scorer
from inspect_ai.solver import (
    Solver,
    solver,
    TaskState,
    Generate,
)
from inspect_ai.util import SandboxEnvironmentSpec, sandbox
from swebench import MAP_REPO_VERSION_TO_SPECS

from multi_agent_eval.environment.agents import AgentConfig, agent_collection_solver
from multi_agent_eval.environment.tools import summarize_tools
from swe_bench_tasks import get_remote_docker_image_from_id, get_sandbox_config_file
from build_images import build_images
from scorers import swe_bench_scorer
from setup_permissions import setup_file_permissions


logger = logging.getLogger(__name__)


def extract_patched_files(patch_text: str) -> List[str]:
    """
    Extract list of files that were patched from a git diff patch.

    Args:
        patch_text: Git diff patch as string

    Returns:
        List of file paths that were modified
    """
    if pd.isna(patch_text) or not isinstance(patch_text, str):
        return []

    # Pattern to match git diff file headers
    # Matches lines like: diff --git a/path/to/file.py b/path/to/file.py
    file_pattern = r"diff --git a/([^\s]+) b/([^\s]+)"

    matches = re.findall(file_pattern, patch_text)

    # Extract unique file paths (use the 'a/' version as it's the original file path)
    files = list(set(match[0] for match in matches))

    return sorted(files)


def get_input_and_augmented_agent_metadata(
    sample: Sample, add_alignment_file: bool = False, solo_agent: bool = False
) -> tuple[str, dict]:
    """
    Generate input message and augmented metadata for SWE-bench task agents.

    Args:
        sample: Sample containing task metadata including patch and problem statement
        add_alignment_file: Whether to add write access to alignment file for inter-agent communication
        solo_agent: Whether to use a single agent for all files (True) or one agent per file (False)

    Returns:
        Tuple of (common_message, augmented_metadata) where common_message is the task description
        and augmented_metadata includes agents_config and required_tests
    """

    # Files that need to be edited to solve the task
    files_to_edit = extract_patched_files(sample.metadata["patch"])
    required_tests = sample.metadata["FAIL_TO_PASS"] + sample.metadata["PASS_TO_PASS"]

    if solo_agent:
        agents_config = [
            AgentConfig(
                id=f"engineer_{0}",
                read_access="ALL",
                write_access=files_to_edit,
                required_tests=required_tests,
                agent_specific_message=dedent(f"""
                    You are responsible for making changes to {files_to_edit} in order to solve the task.
                    Ensure the complete system functions correctly and meets the
                    requirements of the task.
                """),
            )
        ]
    else:
        agents_config = []
        for i, file_name in enumerate(files_to_edit):
            write_access = [file_name]
            if add_alignment_file:
                write_access.append("webserver/align.txt")

            agents_config.append(
                AgentConfig(
                    id=f"engineer_{i}",
                    read_access="ALL",
                    write_access=write_access,
                    required_tests=required_tests,
                    agent_specific_message=dedent(f"""
                        You are responsible for making changes to {file_name} in order to solve the task.
                        Work with other engineers to ensure the complete system functions correctly and meets the
                        requirements of the task.
                    """),
                    message_filter=partial(summarize_tools, keep_last_n=3),
                )
            )

    common_message = dedent(f"""
        The description of your task is:
        {sample.metadata["problem_statement"]}

        {"" if solo_agent else f"There are {len(files_to_edit) - 1} engineers collaborating with you."}

        {
        ""
        if solo_agent
        else (
            (
                "Use the `/workspace/webserver/align.txt` file to share messages with other engineers. "
                "If you are waiting for other engineers to complete their work, you can check this file for messages from other engineers. "
                "First align with the other engineers who implements which interface."
            )
            if add_alignment_file
            else ""
        )
    }

        Ensure all changes are consistent and the tests pass after implementation.
    """)

    # # Uncomment for gold patch testing
    # common_message = "Call the `done()` tool immediately!"

    # # Add alignment file if requested
    # if add_alignment_file:
    #     files["webserver/align.txt"] = "tasks/webserver/align.txt"

    sample.metadata["agents_config"] = agents_config
    sample.metadata["required_tests"] = required_tests

    return common_message, sample.metadata


@solver
def env_setup() -> Solver:
    async def setup(state: TaskState, generate: Generate) -> TaskState:
        test_patch = state.metadata["test_patch"]
        base_commit = state.metadata["base_commit"]
        test_patch_files = re.findall(r"--- a/(.*)", test_patch)
        conda_env = "testbed"
        repo_directory = "/testbed"
        repo = state.metadata["repo"]
        version = state.metadata["version"]
        repo_specific_setup_command = MAP_REPO_VERSION_TO_SPECS[repo][version].get("eval_commands", [])
        repo_specific_install_command = MAP_REPO_VERSION_TO_SPECS[repo][version].get("install", "")

        if repo == "scikit-learn/scikit-learn":  # Scikit-learn gets upset with the install
            repo_specific_install_command = ""

        gold_patch = state.metadata["patch"]

        bash_command = dedent(f"""
            set -uo pipefail -x
    
            #We switch to the repository directory and activate the environment needed to run the tests
            cd {repo_directory}
            set +x
            source /opt/miniconda3/bin/activate
            conda activate {conda_env}
            set -x
    
            #We run all of the repo-specific setup commands (If any exist)
            {"\n".join(repo_specific_setup_command)}
    
            #We make sure we're back in the correct cwd and environment, in case repo setup caused issues.
            cd {repo_directory}
            set +x
            source /opt/miniconda3/bin/activate
            conda activate {conda_env}
            set -x
    
            #We then re-run any repo-specific install commands (these should have happened in environment setup, but we do it again to be sure.)
            {repo_specific_install_command}
    
            #First we reset all of the files which out test patch touches
            git checkout {base_commit} {" ".join(test_patch_files)}
    
    
            # # Apply the golden patch solution for testing
            # echo {shlex.quote(gold_patch)} > /tmp/gold_patch.diff
            # git apply --check /tmp/gold_patch.diff
            # git apply /tmp/gold_patch.diff
            
    
            #Then we apply the test patch given to us by SWE-bench, setting up the test we need to run
            echo {shlex.quote(test_patch)} > /tmp/test_patch.diff
            git apply --check /tmp/test_patch.diff
            git apply /tmp/test_patch.diff
        """)

        result = await sandbox().exec(["bash", "-c", bash_command])
        return state

    return setup


ids = [
    # solved by Inspect Evals agent using gpt-5-codex
    "django__django-14376",
    "django__django-11333",
    "django__django-11532",
    "django__django-12155",
    "django__django-15103",
    "pydata__xarray-3095",
    "pytest-dev__pytest-8399",
]

# ids = [
#     # <15 min fix
#     'django__django-12741',
#     'django__django-13512',
#     'django__django-14315',
#     'django__django-14376',
#     'matplotlib__matplotlib-25479',
#     'sphinx-doc__sphinx-7462',
#
#     # 15 min - 1 hour
#     # 'astropy__astropy-8707', # tests fail with gold patch
#     'django__django-11333',
#     'django__django-11532',
#     'django__django-11734',
#     'django__django-12155',
#     'django__django-12406',
#     'django__django-13121',
#     'django__django-13195',
#     'django__django-14170',
#     'django__django-15103',
#     'django__django-15561',
#     'django__django-15563',
#     'django__django-16032',
#     # 'django__django-16256', # tests fail with gold patch
#     'django__django-16315',
#     'django__django-16938',
#     'matplotlib__matplotlib-14623',
#     'matplotlib__matplotlib-24870',
#     'matplotlib__matplotlib-25775',
#     'mwaskom__seaborn-3187',
#     'pydata__xarray-3095',
#     'pydata__xarray-3305',
#     'pydata__xarray-6938',
#     'pylint-dev__pylint-4604',
#     # 'pylint-dev__pylint-4661', # tests fail with gold patch
#     'pylint-dev__pylint-6386',
#     # 'pylint-dev__pylint-6528', # tests fail with gold patch
#     'pytest-dev__pytest-5840',
#     'pytest-dev__pytest-8399',
#     'scikit-learn__scikit-learn-12682',
#     # 'sphinx-doc__sphinx-10673', # tests fail with gold patch
#     'sphinx-doc__sphinx-8120',
#     'sphinx-doc__sphinx-8551',
#     'sphinx-doc__sphinx-8593',
#     'sympy__sympy-13877',
#     'sympy__sympy-17318',
#     'sympy__sympy-19783',
#     'sympy__sympy-20438',
#     'sympy__sympy-22080',
# ]


@task
def swe_bench(
    dataset: str = "princeton-nlp/SWE-bench_Verified",
    split: str = "test",
    solver: Solver | None = None,
    instance_ids: list[str] | None = ids,
    scorer: Scorer | list[Scorer] | None = None,
    epochs: int = 1,
    sandbox_type: Literal["docker", "k8s"] = "docker",
    build_docker_images: bool = True,
    pull_remote_images_if_available: bool = True,
    docker_image_from_id: Callable[[str], str] = get_remote_docker_image_from_id,
    allow_internet: bool = False,
    sandbox_config_template_file: str | None = None,
    solo_agent: bool = False,
    tools_type: Literal["custom", "bash"] = "custom",
) -> Task:
    """Returns a Task, representing an evaluation on SWE-bench.

    Args.
        dataset : str
            The dataset to use. This should  either be the name of a dataset in the HF hub, or a path to a dataset on disk.
        split : str
            The split of the dataset to load.
        instance_ids : list[str]
            A list of instance_ids to filter the dataset by. If None, all instances are used.
        solver : Solver
            The solver to use when creating the task. If None, uses the default solver.
        scorer : Scorer | list[Scorer] | None
            The scorer to use when evaluating swe_bench. If None, uses the default scorer. Mostly commonly, this will be a list of scorers to compare to baselines (see the README for more information).
        epochs : int
            Number of times to repeat each sample.
        sandbox_type : Literal["docker", "k8s"]
            The type of sandbox to use for the task.
        build_docker_images : bool
            Whether to build the docker images. Implies sandbox_type = "docker". For k8s, you are responsible for building the images yourself, using the original swebench library.
        pull_remote_images_if_available: bool
            If build_docker_images is True, whether to pull the images from DockerHub if available. Defaults to True
        docker_image_from_id : Callable[[str], str]
            Used to transform the swe_bench ID (e.g. astropy__astropy-14182) into a docker container name (e.g. "sweb.eval.x86_64.astropy__astropy-14182:latest"). This is useful if you needed to rebuild the images from the swebench library (e.g. to add tooling) with different names.
            It is also useful as AWS ECR does not allow double underscores in image names, so you can replace them here.
            The default value should be fine if you have built the images using the SWE-Bench library in the normal way.
        allow_internet : bool
            Whether to allow the sandbox to access the internet.
        sandbox_config_template_file : str | None
            Path to a custom sandbox config file template (e.g., compose.yaml for Docker or values.yaml for k8s).
            The file should contain {{IMAGE_NAME}} placeholder which will be replaced with the actual Docker image name for each instance.
        solo_agent : bool
            Whether to use a single agent for all file modifications (True) or one agent per file (False). Defaults to False.

    """
    assert find_spec("swebench"), (
        "To run SWE-bench, please install the optional SWE-bench dependency, by running `uv sync --extra swe_bench`"
    )

    samples = hf_dataset(
        path=dataset,
        split=split,
        sample_fields=FieldSpec(
            input="problem_statement",
            id="instance_id",
            metadata=[
                "base_commit",
                "problem_statement",
                "patch",
                "PASS_TO_PASS",
                "FAIL_TO_PASS",
                "test_patch",
                "version",
                "repo",
                "environment_setup_commit",
                "hints_text",
                "created_at",
            ],
        ),
    )

    if instance_ids is not None:
        samples = samples.filter(lambda x: x.id in instance_ids)

    for sample in samples:
        # Turn the saved strings into list objects
        sample.metadata = sample.metadata or {}
        sample.metadata["PASS_TO_PASS"] = json.loads(sample.metadata["PASS_TO_PASS"])
        sample.metadata["FAIL_TO_PASS"] = json.loads(sample.metadata["FAIL_TO_PASS"])
        sample.input, sample.metadata = get_input_and_augmented_agent_metadata(sample, solo_agent=solo_agent)

    if build_docker_images:
        if sandbox_type != "docker":
            raise ValueError(
                "If you want to use k8s, you are responsible for building the images yourself, using the original swebench library."
            )
        # Build the images for the samples - can take a long time
        id_to_docker_image_map = build_images(
            samples=samples,
            force_rebuild=False,
            use_remote_images=pull_remote_images_if_available,
        )

        # If using bash tools, setup file permissions per agent
        if tools_type == "bash":
            from docker.client import DockerClient

            docker_client = DockerClient.from_env()

            # Create restricted images for each instance
            for sample in samples:
                instance_id = str(sample.id)
                base_image = id_to_docker_image_map[instance_id]
                agent_configs = sample.metadata["agents_config"]

                # Setup file permissions for this instance's agents
                restricted_image = setup_file_permissions(
                    docker_client=docker_client,
                    image_name=base_image,
                    agent_configs=agent_configs,
                    working_dir="/testbed",
                )

                # Update the image map to use the restricted image
                id_to_docker_image_map[instance_id] = restricted_image

            logger.info(f"Set up file permissions for {len(samples)} instances")

        # Replace docker_image_from_id function with authoritative source
        def get_docker_image(instance_id: str) -> str:
            return id_to_docker_image_map.get(instance_id, "")

        docker_image_from_id = get_docker_image

    for sample in samples:
        sample.metadata = sample.metadata or {}
        sample.sandbox = SandboxEnvironmentSpec(
            type=sandbox_type,
            config=get_sandbox_config_file(
                instance_id=str(sample.id),
                docker_image_from_id=docker_image_from_id,
                allow_internet=allow_internet,
                sandbox_type=sandbox_type,
                sandbox_config_template_file=sandbox_config_template_file,
            ),
        )

    return Task(
        dataset=samples,
        setup=env_setup(),
        solver=solver
        or agent_collection_solver(
            tools_type=tools_type,
            test_tool_func_type="swe_bench",
        ),
        epochs=epochs,
        scorer=scorer or swe_bench_scorer(),
        message_limit=80,
    )
