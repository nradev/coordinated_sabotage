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
            if wait_time > 20:
                return f"[{agent_id}] is not allowed to wait for longer than 10 seconds."

            await asyncio.sleep(wait_time)

            return f"[{agent_id}] has waited for {wait_time} seconds."

        return execute

    return wait()


def create_grep_tool(agent_id: str, read_access: List[str] | None = None, working_dir: str | None = None) -> Tool:
    """
    Create a tool to search for patterns in files using grep.
    If read_access is None, there are no restrictions.
    """

    @tool
    def grep():
        async def execute(pattern: str, file_path: str = ".", options: str = "") -> str:
            """
            Search for patterns in files using grep.

            Args:
                pattern: The pattern to search for (regex supported)
                file_path: File or directory to search in (default: current directory)
                options: Additional grep options as a string (e.g., "-r" for recursive, "-i" for case-insensitive,
                        "-n" for line numbers, "-l" for filenames only). Multiple options can be combined (e.g., "-rn").

            Returns:
                Matching lines from the search
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                # Ensure the file path is within the repo
                if file_path.startswith("/") or ".." in file_path:
                    raise ToolError(f"[{agent_id}] Invalid file path. Use relative paths within the repo.")

                # Check read permissions for this agent
                # For recursive searches or directory searches, we can't check all files upfront,
                # so we only check if a specific file is provided
                if read_access is not None and file_path != ".":
                    # Check if this is a specific file (not a directory or recursive search)
                    is_recursive = "-r" in options or "-R" in options
                    if not is_recursive and file_path not in read_access:
                        raise ToolError(f"[{agent_id}] only has read access to {read_access}. Cannot grep {file_path}")

                path = file_path
                if working_dir is not None:
                    if path == ".":
                        path = working_dir
                    else:
                        path = f"{working_dir}/{path}"

                # Build grep command
                cmd = ["grep"]
                if options:
                    # Split options but be careful about option arguments
                    cmd.extend(shlex.split(options))

                # Add the pattern (use -- to separate options from pattern in case pattern starts with -)
                cmd.append("--")
                cmd.append(pattern)
                cmd.append(path)

                result = await sandbox_env.exec(cmd)

                # grep returns 0 if matches found, 1 if no matches, 2+ for errors
                if result.returncode > 1:
                    raise ToolError(
                        f"[{agent_id}] Error running grep:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                    )

                if result.returncode == 1:
                    return f"[{agent_id}] No matches found for pattern '{pattern}' in {file_path}"

                return f"[{agent_id}] Grep results for pattern '{pattern}' in {file_path}:\n{result.stdout}"

            except ToolError:
                raise
            except Exception as e:
                raise ToolError(f"[{agent_id}] Error running grep: {str(e)}")

        return execute

    return grep()


def create_patch_tool(
    agent_id: str,
    write_access: List[str] | None = None,
    validators: List[Callable] | None = None,
    modifiers: List[Callable] | None = None,
    working_dir: str | None = None,
) -> Tool:
    """
    Create a tool to apply unified diff patches to files.
    If write_access is None, there are no restrictions.
    """

    # TODO figure out why models can't seem to get the patch format right
    @tool
    def patch():
        async def execute(patch_content: str, strip_level: int = 1) -> str:
            """
            Apply a unified diff patch to files. Use the standard 'diff -u' format.

            Args:
                patch_content: Unified diff format only. Must start with '--- a/' and '+++ b/' headers.
                    Format requirements:
                    1. File header: --- a/path/to/file.py
                    2. File header: +++ b/path/to/file.py
                    3. Hunk header: @@ -start,count +start,count @@
                    4. Context lines MUST start with space ' '
                    5. Removed lines start with '-'
                    6. Added lines start with '+'

                    Example (note the leading space on 'def foo():'):
                    --- a/file.py
                    +++ b/file.py
                    @@ -1,3 +1,3 @@
                     def foo():
                    -    return 1
                    +    return 2

                    DO NOT use custom formats like '*** Begin Patch' or '*** Update File:'.
                    DO NOT use bare '@@' without line numbers.

                strip_level: Number of leading path components to strip (default: 1)

            Returns:
                Success message or error
            """
            try:
                sandbox_env = sandbox()
                if not sandbox_env:
                    raise ToolError(f"[{agent_id}] Sandbox environment not available")

                # Clean up patch content
                patch_content = patch_content.strip()
                lines = patch_content.split("\n")

                # Check for and reject custom patch formats
                first_line = lines[0] if lines else ""
                if first_line.startswith("*** Begin Patch") or first_line.startswith("*** Update File"):
                    raise ToolError(
                        f"[{agent_id}] Invalid patch format detected.\n\n"
                        f"You used a custom format starting with '{first_line[:30]}'.\n"
                        f"This tool ONLY accepts standard unified diff format.\n\n"
                        f"Required format:\n"
                        f"--- a/path/to/file\n"
                        f"+++ b/path/to/file\n"
                        f"@@ -line,count +line,count @@\n"
                        f" context line (note leading space)\n"
                        f"-removed line\n"
                        f"+added line\n"
                    )

                # Remove common trailing markers that models add
                trailing_markers = [
                    "*** End Patch",
                    "*** END PATCH",
                    "End Patch",
                    "END PATCH",
                    "```",
                ]
                for marker in trailing_markers:
                    if patch_content.endswith(marker):
                        patch_content = patch_content[: -len(marker)].rstrip()
                        lines = patch_content.split("\n")  # Re-split after cleanup
                errors = []

                # Check for basic patch structure
                has_old_file_header = any(line.startswith("---") for line in lines)
                has_new_file_header = any(line.startswith("+++") for line in lines)
                has_hunk_header = any(line.startswith("@@") and "@@" in line[2:] for line in lines)

                if not has_old_file_header:
                    errors.append("Missing '--- a/filename' header (old file marker)")
                if not has_new_file_header:
                    errors.append("Missing '+++ b/filename' header (new file marker)")
                if not has_hunk_header:
                    errors.append("Missing '@@ -line,count +line,count @@' hunk header")

                # Validate hunk lines
                in_hunk = False
                for i, line in enumerate(lines, 1):
                    if line.startswith("@@"):
                        in_hunk = True
                        # Validate hunk header format
                        if not re.match(r"^@@\s+-\d+(?:,\d+)?\s+\+\d+(?:,\d+)?\s+@@", line):
                            errors.append(f"Line {i}: Invalid hunk header format: {line[:50]}")
                    elif in_hunk and line and not line.startswith(("---", "+++")):
                        # Every line in a hunk must start with space, +, -, or be a new file marker
                        if not line[0] in (" ", "+", "-", "\\"):
                            errors.append(
                                f"Line {i}: Context line missing leading space. "
                                f"Line starts with: {repr(line[0])} (full line: {line[:50]}...)"
                            )

                if errors:
                    error_msg = "\n".join(errors)
                    raise ToolError(
                        f"[{agent_id}] Invalid patch format:\n{error_msg}\n\n"
                        f"REMINDER: Context lines (unchanged code) MUST start with a space character."
                    )

                # Extract files that will be modified from the patch
                # Match both "+++ b/path" and "+++ path" formats
                modified_files_raw = re.findall(r"^\+\+\+ (.+?)(?:\s|$)", patch_content, re.MULTILINE)

                # Strip the appropriate number of path components based on strip_level
                modified_files = []
                for file_path in modified_files_raw:
                    # Remove trailing whitespace/timestamp if present
                    file_path = file_path.split()[0] if file_path.split() else file_path

                    # Apply strip level
                    parts = file_path.split("/")
                    if strip_level < len(parts):
                        stripped_path = "/".join(parts[strip_level:])
                        modified_files.append(stripped_path)
                    elif strip_level == 0:
                        modified_files.append(file_path)

                # Check write permissions for all files that will be modified
                if write_access is not None:
                    for file_path in modified_files:
                        if file_path not in write_access:
                            raise ToolError(
                                f"[{agent_id}] only has write access to {write_access}. Cannot patch {file_path}"
                            )

                # Run validators if provided
                for validator in validators or []:
                    for file_path in modified_files:
                        await validator(patch_content, agent_id, file_path, sandbox_env, write_access)

                # Run modifiers if provided
                for modifier in modifiers or []:
                    for file_path in modified_files:
                        patch_content = await modifier(patch_content, agent_id, file_path, sandbox_env, write_access)

                # Write patch to temporary file
                patch_file_path = f"/tmp/{agent_id}_patch.diff"
                await sandbox_env.write_file(patch_file_path, patch_content)

                # Apply patch
                path = "."
                if working_dir is not None:
                    path = working_dir

                result = await sandbox_env.exec(
                    ["bash", "-c", f"cd {path} && patch -p{strip_level} < {patch_file_path}"]
                )

                if result.returncode != 0:
                    raise ToolError(
                        f"[{agent_id}] Error applying patch:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                    )

                # Log the modification for each file
                for file_path in modified_files:
                    log_path = f"{SANDBOX_WORKSPACE}/.agent_logs/{agent_id}_modifications.log"
                    log_entry = f"Patched {file_path} at step {asyncio.current_task().get_name()}\n"

                    try:
                        existing_log = await sandbox_env.read_file(log_path)
                        await sandbox_env.write_file(log_path, existing_log + log_entry)
                    except FileNotFoundError:
                        await sandbox_env.write_file(log_path, log_entry)

                files_msg = ", ".join(modified_files) if modified_files else "files"
                return f"[{agent_id}] Successfully applied patch to: {files_msg}\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"

            except ToolError:
                raise
            except Exception as e:
                raise ToolError(f"[{agent_id}] Error applying patch: {str(e)}")

        return execute

    return patch()


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


async def summarize_tools_per_file(
    messages: list[ChatMessage],
    keep_last_n: int = 1,
) -> list[ChatMessage]:
    """Summarize tool calls from messages, tracking reads per file.

    Args:
       messages: Messages to summarize tool calls from.
       keep_last_n: The number of most recent tool call messages to keep per file.

    Returns:
       Messages with summarized tool calls.

    """
    from collections import defaultdict

    # Track counts per file for read operations
    read_counts_per_file: dict[str, int] = defaultdict(int)
    write_counts_per_file: dict[str, int] = defaultdict(int)

    # First pass: count operations per file
    for message in messages:
        if isinstance(message, ChatMessageTool):
            if message.function == "read_file":
                # Extract file_path from the message content
                # Format is typically "[agent_id] Successfully read {file_path}:\n..."
                try:
                    first_line = message.content.split("\n")[0]
                    if "Successfully read" in first_line:
                        file_path = first_line.split("Successfully read ")[1].rstrip(":")
                        read_counts_per_file[file_path] += 1
                except (IndexError, AttributeError):
                    pass
            elif message.function == "write_file":
                # Extract file_path from the message content
                # Format is typically "[agent_id] Successfully wrote to {file_path}"
                try:
                    if "Successfully wrote to" in message.content:
                        file_path = message.content.split("Successfully wrote to ")[1].strip()
                        write_counts_per_file[file_path] += 1
                except (IndexError, AttributeError):
                    pass

    # Track remaining counts to keep per file
    remaining_reads_per_file = {fp: count for fp, count in read_counts_per_file.items()}
    remaining_writes_per_file = {fp: count for fp, count in write_counts_per_file.items()}

    n_run_tests = sum([m.function == "run_tests" for m in messages if isinstance(m, ChatMessageTool)])

    # Track write_file calls in assistant messages
    write_file_calls_per_file: dict[str, int] = defaultdict(int)
    for message in messages:
        if isinstance(message, ChatMessageAssistant) and message.tool_calls:
            for tc in message.tool_calls:
                if tc.function == "write_file":
                    try:
                        file_path = tc.arguments.get("file_path", "")
                        if file_path:
                            write_file_calls_per_file[file_path] += 1
                    except (AttributeError, KeyError):
                        pass

    remaining_write_calls_per_file = {fp: count for fp, count in write_file_calls_per_file.items()}

    filtered: list[ChatMessage] = []
    for message in messages:
        if isinstance(message, ChatMessageTool):
            summarize = False

            if message.function == "read_file":
                try:
                    first_line = message.content.split("\n")[0]
                    if "Successfully read" in first_line:
                        file_path = first_line.split("Successfully read ")[1].rstrip(":")
                        if remaining_reads_per_file.get(file_path, 0) > keep_last_n:
                            summarize = True
                            remaining_reads_per_file[file_path] -= 1
                except (IndexError, AttributeError):
                    pass

            elif message.function == "write_file":
                try:
                    if "Successfully wrote to" in message.content:
                        file_path = message.content.split("Successfully wrote to ")[1].strip()
                        if remaining_writes_per_file.get(file_path, 0) > keep_last_n:
                            summarize = True
                            remaining_writes_per_file[file_path] -= 1
                except (IndexError, AttributeError):
                    pass

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
                    if tool_call.function == "write_file":
                        try:
                            file_path = tool_call.arguments.get("file_path", "")
                            if file_path and remaining_write_calls_per_file.get(file_path, 0) > keep_last_n:
                                remaining_write_calls_per_file[file_path] -= 1
                                tool_call.arguments["content"] = "[CONTENT_WAS_TRUNCATED_FOR_BREVITY]"
                        except (AttributeError, KeyError):
                            pass
                    tool_calls.append(tool_call)
                message = message.model_copy(update=dict(tool_calls=tool_calls))

        filtered.append(message)

    return filtered
