import asyncio
from typing import Optional, List, Callable

from inspect_ai.agent import AgentSubmit
from inspect_ai.tool import Tool, tool, ToolError
from inspect_ai.util import sandbox
from loguru import logger

# TODO: this should be defined somewhere else, but then it is not triggered -> good enough for now
logger.add(
    "../logs/eval_{time}.log",
    level="DEBUG",
)


def create_file_reader_tool(agent_id: str, read_access: List[str] | None = None) -> Tool:
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
                    raise ToolError(f"[Agent {agent_id}] Sandbox environment not available")

                # Check read permissions for this agent
                if read_access is not None and file_path not in read_access:
                    raise ToolError(
                        f"[Agent {agent_id}] only has read access to {read_access}. Cannot read from {file_path}"
                    )

                # Ensure the file path is within the repo
                if file_path.startswith("/") or ".." in file_path:
                    raise ToolError(f"[Agent {agent_id}] Invalid file path. Use relative paths within the repo.")

                logger.debug(f"[Agent {agent_id}] Reading file {file_path}.")

                contents = await sandbox_env.read_file(f"/workspace/{file_path}")
                return f"[Agent {agent_id}] Successfully read {file_path}:\n{contents}"

            except FileNotFoundError:
                raise ToolError(f"[Agent {agent_id}] File {file_path} not found")
            except Exception as e:
                msg = f"[Agent {agent_id}] Error reading file: {str(e)}"
                logger.exception(msg)
                raise ToolError(msg)

        return execute

    return read_file()


def create_file_writer_tool(
    agent_id: str,
    write_access: List[str] | None = None,
    validators: List[Callable] | None = None,
    modifiers: List[Callable] | None = None,
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
                    raise ToolError(f"[Agent {agent_id}] Sandbox environment not available")

                # Check write permissions for this agent
                if write_access is not None and file_path not in write_access:
                    raise ToolError(
                        f"[Agent {agent_id}] only has write access to {write_access}. Cannot write to {file_path}"
                    )

                for validator in validators or []:
                    await validator(content, agent_id, file_path, sandbox_env, write_access)

                for modifier in modifiers or []:
                    content = await modifier(content, agent_id, file_path, sandbox_env, write_access)

                # Write the file
                await sandbox_env.write_file(f"/workspace/{file_path}", content)

                # Log the modification
                log_path = f"/workspace/.agent_logs/{agent_id}_modifications.log"
                log_entry = f"Modified {file_path} at step {asyncio.current_task().get_name()}\n"

                logger.debug(f"[Agent {agent_id}] Writing file {file_path}: {content}.")
                try:
                    existing_log = await sandbox_env.read_file(log_path)
                    await sandbox_env.write_file(log_path, existing_log + log_entry)
                except FileNotFoundError:
                    await sandbox_env.write_file(log_path, log_entry)

                return f"[Agent {agent_id}] Successfully wrote to {file_path}"

            except ToolError:
                raise
            except Exception as e:
                msg = f"[Agent {agent_id}] Error writing file: {str(e)}"
                logger.exception(msg)
                raise ToolError(msg)

        return execute

    return write_file()


def create_list_files_tool(agent_id: str) -> Tool:
    """Create a tool to list all Python files in the repository."""

    @tool
    def list_files():
        async def execute(directory: str = ".") -> str:
            """
            List all Python files in the specified directory.

            Args:
                directory: Directory to list files from (default: repo root)

            Returns:
                List of Python files in the directory
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[Agent {agent_id}] Sandbox environment not available")

                # Execute ls command to list Python files
                result = await sandbox_env.exec(["find", f"/workspace/{directory}", "-name", "*.py", "-type", "f"])

                if result.returncode != 0:
                    raise ToolError(f"[Agent {agent_id}] Error listing files: {result.stderr}")

                files = result.stdout.strip().split("\n")
                files = [f.replace("/workspace/", "") for f in files if f]

                logger.debug(f"[Agent {agent_id}] Found files: {files}")

                return f"[Agent {agent_id}] Python files in {directory}:\n" + "\n".join(files)

            except Exception as e:
                msg = f"[Agent {agent_id}] Error listing files: {str(e)}"
                logger.exception(msg)
                raise ToolError(msg)

        return execute

    return list_files()


def create_run_tests_tool(agent_id: str) -> Tool:
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
                    raise ToolError(f"[Agent {agent_id}] Sandbox environment not available")

                if test_file:
                    cmd = ["python", "-m", "pytest", f"/workspace/{test_file}", "-v"]
                else:
                    cmd = ["python", "-m", "pytest", "/workspace", "-v"]

                result = await sandbox_env.exec(cmd)

                return f"[Agent {agent_id}] Test results:\n{result.stdout}\n{result.stderr}"

            except Exception as e:
                raise ToolError(f"[Agent {agent_id}] Error running tests: {str(e)}")

        return execute

    return run_tests()


def create_wait_tool(agent_id: str) -> Tool:
    """Create a tool to indicate that the agent is done with all file edits."""

    @tool
    def wait():
        async def execute(wait_time: int = 1) -> str:
            """
            Indicates that the agent wants to wait for actions by other agents e.g. edits to other files.

            Args:
                wait_time: Desired wait time (in seconds). Must be greater than 0 and less than or equal to 20.

            Returns:
                Message indicating the wait time has elapsed.
            """
            logger.debug(f"[Agent {agent_id}] Waiting for {wait_time} seconds.")
            if wait_time > 20:
                return f"Agent {agent_id} is not allowed to wait for longer than 10 seconds."

            await asyncio.sleep(wait_time)

            logger.debug(f"[Agent {agent_id}] Waited for {wait_time} seconds.")

            return f"Agent {agent_id} has waited for {wait_time} seconds."

        return execute

    return wait()


def create_done_tool(agent_id: str) -> AgentSubmit:
    """Create a tool to indicate that the agent is done with all file edits."""

    @tool(name="done")
    def done_tool():
        async def execute() -> str:
            """Indicate that the agent is done with all file edits."""
            msg = f"Agent {agent_id} is done."
            logger.debug(msg)
            return msg

        return execute

    return AgentSubmit(
        name="done",
        description="Indicate that the agent is done with all file edits.",
        tool=done_tool(),
    )
