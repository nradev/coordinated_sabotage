import asyncio
import re
import shlex
from textwrap import dedent
from typing import Optional, List, Callable

from inspect_ai.agent import AgentSubmit
from inspect_ai.model import ChatMessage, ChatMessageTool, ChatMessageAssistant
from inspect_ai.tool import Tool, tool, ToolError
from inspect_ai.util import sandbox
from swebench import MAP_REPO_VERSION_TO_SPECS
from swebench.harness.test_spec.python import get_test_directives

from .constants import SANDBOX_WORKSPACE


# TODO consider returning a diff on subsequent file reads?
def create_file_reader_tool(
    agent_id: str, read_access: List[str] | None = None, working_dir: str | None = None
) -> Tool:
    """
    Create a file writing tool with agent-specific write permissions.
    If read_access is None, there are no restrictions.
    """

    @tool
    def read_file():
        async def execute(file_path: str) -> str:
            """
            Read the contents of a Python file.

            Args:
                file_path: Path to the file to read (relative to repo root)

            Returns:
                The contents of the file
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                # Check read permissions for this agent
                if read_access is not None and file_path not in read_access:
                    raise ToolError(f"[{agent_id}] only has read access to {read_access}. Cannot read from {file_path}")

                # Ensure the file path is within the repo
                if file_path.startswith("/") or ".." in file_path:
                    raise ToolError(f"[{agent_id}] Invalid file path. Use relative paths within the repo.")

                path = file_path
                if working_dir is not None:
                    path = f"{working_dir}/{path}"

                contents = await sandbox_env.read_file(path)
                return f"[{agent_id}] Successfully read {file_path}:\n{contents}"

            except FileNotFoundError:
                raise ToolError(f"[{agent_id}] File {file_path} not found")
            except Exception as e:
                raise ToolError(f"[{agent_id}] Error reading file: {str(e)}")

        return execute

    return read_file()


def create_file_writer_tool(
    agent_id: str,
    write_access: List[str] | None = None,
    validators: List[Callable] | None = None,
    modifiers: List[Callable] | None = None,
    working_dir: str | None = None,
) -> Tool:
    """
    Create a file writing tool with agent-specific write permissions.
    If write_access is None, there are no restrictions.
    """

    @tool
    def write_file():
        async def execute(file_path: str, content: str) -> str:
            """
            Write content to a Python file (restricted by agent permissions).

            Args:
                file_path: Path to the file to write (relative to repo root)
                content: The content to write to the file

            Returns:
                Success message or error
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                # Check write permissions for this agent
                if write_access is not None and file_path not in write_access:
                    raise ToolError(
                        f"[{agent_id}] only has write access to {write_access}. Cannot write to {file_path}"
                    )

                for validator in validators or []:
                    await validator(content, agent_id, file_path, sandbox_env, write_access)

                for modifier in modifiers or []:
                    content = await modifier(content, agent_id, file_path, sandbox_env, write_access)

                # Write the file
                path = file_path
                if working_dir is not None:
                    path = f"{working_dir}/{path}"
                await sandbox_env.write_file(f"{path}", content)

                # Log the modification
                # TODO figure out what to do with this
                log_path = f"{SANDBOX_WORKSPACE}/.agent_logs/{agent_id}_modifications.log"
                log_entry = f"Modified {file_path} at step {asyncio.current_task().get_name()}\n"

                try:
                    existing_log = await sandbox_env.read_file(log_path)
                    await sandbox_env.write_file(log_path, existing_log + log_entry)
                except FileNotFoundError:
                    await sandbox_env.write_file(log_path, log_entry)

                return f"[{agent_id}] Successfully wrote to {file_path}"

            except ToolError:
                raise
            except Exception as e:
                raise ToolError(f"[{agent_id}] Error writing file: {str(e)}")

        return execute

    return write_file()


def create_list_files_and_directories_tool(agent_id: str, working_dir: str | None = None) -> Tool:
    """Create a tool to list all Python files and directories in the repository."""

    @tool
    def list_files_and_directories():
        async def execute(directory: str = ".") -> str:
            """
            List all files and directories in the specified directory.

            Args:
                directory: Directory to list files and directories from (default: repo root)

            Returns:
                List of files and directories in the directory
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                # Execute ls command to list files
                path = directory
                if working_dir is not None:
                    path = f"{working_dir}/{path}"
                result = await sandbox_env.exec(["ls", path])

                if result.returncode != 0:
                    raise ToolError(f"[{agent_id}] Error listing files and directories: {result.stderr}")

                files = result.stdout.strip().split("\n")
                files = [f.replace(f"{working_dir}/", "") for f in files if f]

                return f"[{agent_id}] files in and directories {directory}:\n" + "\n".join(files)

            except Exception as e:
                raise ToolError(f"Error listing files and directories: {str(e)}")

        return execute

    return list_files_and_directories()


def create_run_tests_tool(
    agent_id: str,
    required_tests: list[str] | None = None,
    working_dir: str | None = None,
) -> Tool:
    """Create a tool to run tests and validate changes."""

    @tool
    def run_tests():
        async def execute(test_file: Optional[str] = None) -> str:
            """
            Run Python tests to validate the changes.

            Args:
                test_file: Specific test file to run (optional)

            Returns:
                Test results
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                if required_tests is not None:
                    if working_dir is not None:
                        tests = [f"{working_dir}/{t}" for t in required_tests]
                    else:
                        tests = required_tests
                    cmd = ["python", "-m", "pytest", " ".join(tests), "-v"]
                else:
                    path = test_file or ""
                    if working_dir is not None:
                        path = f"{working_dir}/{path}"
                    cmd = ["python", "-m", "pytest", path, "-v"]

                result = await sandbox_env.exec(cmd)

                return f"[{agent_id}] Test results:\n{result.stdout}\n{result.stderr}"

            except Exception as e:
                raise ToolError(f"[{agent_id}] Error running tests: {str(e)}")

        return execute

    return run_tests()


# TODO consider adding an option to return only pass/fail info (no other output)
def create_run_tests_tool_SWE_bench(
    agent_id: str,
    state,
    required_tests: list[str] | None = None,
    working_dir: str | None = None,
) -> Tool:
    """Create a tool to run tests and validate changes."""

    @tool
    def run_tests():
        async def execute() -> str:
            """
            Run Python tests to validate the changes.

            Returns:
                Test results
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                conda_env = "testbed"
                repo_directory = "/testbed"
                test_patch = state.metadata["test_patch"]
                repo = state.metadata["repo"]
                version = state.metadata["version"]
                base_commit = state.metadata["base_commit"]

                # Fetch the command which runs the test. Often simply the string 'pytest'
                test_command = MAP_REPO_VERSION_TO_SPECS[repo][version]["test_cmd"]

                # Fetch any repo-specific setup commands, e.g. any environment variables
                repo_specific_setup_command = MAP_REPO_VERSION_TO_SPECS[repo][version].get("eval_commands", [])

                repo_specific_install_command = MAP_REPO_VERSION_TO_SPECS[repo][version].get("install", "")

                if repo == "scikit-learn/scikit-learn":  # Scikit-learn gets upset with the install
                    repo_specific_install_command = ""

                # Find all the files which have been modified by the test patch
                test_patch_files = re.findall(r"--- a/(.*)", test_patch)

                # Find all the files which contain tests. Ugly interface is due to swebench
                test_files = get_test_directives({"repo": repo, "test_patch": test_patch})

                newline = "\n"
                bash_command = dedent(f"""
                    #We switch to the repository directory and activate the environment needed to run the tests
                    cd {repo_directory}
                    set +x
                    source /opt/miniconda3/bin/activate
                    conda activate {conda_env}
                    set -x

                    #We run all of the repo-specific setup commands (If any exist)
                    {newline.join(repo_specific_setup_command)}

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

                    #Then we apply the test patch given to us by SWE-bench, setting up the test we need to run
                    echo {shlex.quote(test_patch)} > /tmp/test_patch.diff
                    git apply --check /tmp/test_patch.diff
                    git apply /tmp/test_patch.diff
            
                    #Then we run all the tests in the repository.
                    set +x
                    {test_command} {" ".join(test_files)} || true
                """)

                result = await sandbox_env.exec(["bash", "-c", bash_command])

                return f"[{agent_id}] Test results:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

            except Exception as e:
                raise ToolError(f"[{agent_id}] Error running tests: {str(e)}")

        return execute

    return run_tests()


def create_wait_tool(agent_id: str) -> Tool:
    """Create a tool to indicate that the agent is done with all file edits."""

    @tool
    def wait():
        async def execute(wait_time: int = 1) -> str:
            """
            Indicates an intention to wait for actions by others.

            Args:
                wait_time: Desired wait time (in seconds). Must be greater than 0 and less than or equal to 20.

            Returns:
                Message indicating the wait time has elapsed.
            """
            logger.debug(f"[Agent {agent_id}] Waiting for {wait_time} seconds.")
            if wait_time > 20:
                return f"[{agent_id}] is not allowed to wait for longer than 10 seconds."

            await asyncio.sleep(wait_time)

            return f"[{agent_id}] has waited for {wait_time} seconds."

        return execute

    return wait()


def create_done_tool(agent_id: str) -> AgentSubmit:
    """Create a tool to indicate that the agent is done with all file edits."""

    @tool(name="done")
    def done_tool():
        async def execute() -> str:
            """Indicate that the work is complete."""
            return f"[{agent_id}] is done."

        return execute

    return AgentSubmit(
        name="done",
        description="Indicate that the work is complete.",
        tool=done_tool(),
    )


# TODO somehow log the full tool content in the logs so it is visible in the timeline
async def summarize_tools(
    messages: list[ChatMessage],
    keep_last_n: int = 1,
) -> list[ChatMessage]:
    """Summarize tool calls from messages.

    Args:
       messages: Messages to summarize tool calls from.
       keep_last_n: The number of most recent tool call (by type) messages to keep.

    Returns:
       Messages with summarized tool calls.

    """
    # TODO use read/write counts by file in addition to the cumulative
    n_write_file = sum([m.function == "write_file" for m in messages if isinstance(m, ChatMessageTool)])
    n_read_file = sum([m.function == "read_file" for m in messages if isinstance(m, ChatMessageTool)])
    n_run_tests = sum([m.function == "run_tests" for m in messages if isinstance(m, ChatMessageTool)])

    # for now we count instances with multiple write tool calls as one; could reconsider
    n_write_file_calls = sum(
        [
            any([tc.function == "write_file" for tc in m.tool_calls])
            for m in messages
            if isinstance(m, ChatMessageAssistant) and m.tool_calls is not None
        ]
    )

    filtered: list[ChatMessage] = []
    for message in messages:
        if isinstance(message, ChatMessageTool):
            summarize = False
            # TODO consider adding actual summarization text
            if message.function == "write_file" and n_write_file > keep_last_n:
                summarize = True
                n_write_file -= 1
            elif message.function == "read_file" and n_read_file > keep_last_n:
                summarize = True
                n_read_file -= 1
            elif message.function == "run_tests" and n_run_tests > keep_last_n:
                summarize = True
                n_run_tests -= 1
            if summarize:
                message = message.model_copy(
                    update=dict(
                        content=message.content.split("\n")[0] + "\n[CONTENT_WAS_TRUNCATED_FOR_BREVITY]",
                        text=message.text.split("\n")[0] + "\n[CONTENT_WAS_TRUNCATED_FOR_BREVITY]",
                    )
                )
        elif isinstance(message, ChatMessageAssistant):
            if message.tool_calls:
                tool_calls = []
                for tool_call in message.tool_calls:
                    if tool_call.function == "write_file" and n_write_file_calls > keep_last_n:
                        n_write_file_calls -= 1
                        tool_call.arguments["content"] = "[CONTENT_WAS_TRUNCATED_FOR_BREVITY]"
                    tool_calls.append(tool_call)
                message = message.model_copy(update=dict(tool_calls=tool_calls))
        filtered.append(message)

    return filtered
