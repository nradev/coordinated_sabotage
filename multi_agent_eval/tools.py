import asyncio
from textwrap import dedent
from typing import Optional, List, Callable

from inspect_ai.agent import AgentSubmit
from inspect_ai.tool import Tool, tool, ToolError
from inspect_ai.util import sandbox

from constants import SANDBOX_WORKSPACE


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


def create_run_tests_tool_SWE_bench(
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

                # Environment setup with conda activation
                repo_directory = working_dir or "/testbed"
                conda_env = "testbed"

                # Prepare test command
                if required_tests is not None:
                    if working_dir is not None:
                        tests = [f"{working_dir}/{t}" for t in required_tests]
                    else:
                        tests = required_tests
                    test_cmd = f"python -m pytest {' '.join(tests)} -v"
                else:
                    path = test_file or ""
                    if working_dir is not None:
                        path = f"{working_dir}/{path}"
                    test_cmd = f"python -m pytest {path} -v"

                bash_command = dedent(
                    f"""set -uo pipefail -x
                    cd {repo_directory}
                    set +x
                    source /opt/miniconda3/bin/activate
                    conda activate {conda_env}
                    set -x
                    {test_cmd}"""
                )

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
