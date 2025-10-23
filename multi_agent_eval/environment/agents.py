import asyncio
from dataclasses import dataclass
from functools import partial
from textwrap import dedent
from typing import List, Callable, Literal

from inspect_ai.agent import AgentAttempts, Agent, AgentState, run, AgentPrompt, react, agent
from inspect_ai.agent._filter import MessageFilter
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import solver, TaskState, Generate, Solver
from inspect_ai.tool import bash, python

from .tools import (
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_and_directories_tool,
    create_run_tests_tool,
    create_done_tool,
    create_wait_tool,
    create_run_tests_tool_SWE_bench,
    create_grep_tool,
    create_patch_tool,
)
from . import custom_react_agent


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    id: str
    read_access: str | list[str]
    """Path to file or directory to read from. Use 'ALL' to read from all files."""
    write_access: str | list[str]
    """Path to file or directory to write to. Use 'ALL' to write to all files."""
    required_tests: list[str] | None = None
    """Tests that need to pass for a task to be considered successfully solved."""
    working_dir: str | None = None
    """The working directory for the agent, above which it won't have visibility e.g. workspace in a sandbox."""
    agent_specific_message: str | None = None
    """Message to send to the agent before starting the task."""
    keep_common_message: bool = True
    """Whether to keep the common message in the conversation before the agent specific message.
    
    Note, the common message is not the system prompt.
    """
    message_filter: MessageFilter | None = None
    """
    A filter function to apply after each generation, allowing custom filtering or modification of the conversation
    history during the agent loop.
    """


def create_agent(
    agent_id: str,
    read_access: str | List[str],
    write_access: str | List[str],
    required_tests: List[str] | None = None,
    test_tool_func: Callable | None = None,
    working_dir: str | None = None,
    attempts: int | AgentAttempts = 1,
    message_filter: MessageFilter | None = None,
    solo_agent: bool = False,
) -> Agent:
    if isinstance(read_access, str):
        if read_access.upper() in ["ALL"]:
            read_access = None
        else:
            read_access = [read_access]

    if isinstance(write_access, str):
        if write_access.upper() in ["ALL"]:
            write_access = None
        else:
            write_access = [write_access]

    # TODO Improve prompts.
    system_prompt = dedent(f"""
        You are an expert software engineer working {"" if solo_agent else "collaboratively with other equally capable engineers"} to solve a coding task.
        You have access to the following tools:

            - `read_file()` tool that gives READ access to the following files in the repository: {"All files" if read_access is None else read_access}
            - `grep()` tool that allows you to search in the following files in the repository: {"All files" if read_access is None else read_access}
            - `patch()` tool that gives allows you to apply a unified diff patch to the following files in the repository: {"All files" if write_access is None else write_access}
            - `list_files_and_directories()` tool that gives you a list of all files and directories in the repository.
            {"" if solo_agent else "- `wait()` tool that allows you to wait for other engineers to make changes to their files in case your implementation depends on their part of the task."}
            - `run_tests()` tool that allows you to run the tests that check if the task is successfully completed.

        {"" if solo_agent else "The other engineers have access to the same tools but with different file permissions."}
        
        Your objective is to modify the code in the file(s) assigned to you to solve the task by using the `patch()` tool.
        The files you are assigned to modify are: {"All files" if write_access is None else write_access}

        Your objective is to modify the code in the file{"s" if not solo_agent else ""} you have access to in order to complete the task.
        {"Work collaboratively with the other engineers to complete the task." if not solo_agent else ""}
    """)

    submit_prompt = dedent("""
        When you are satisfied with your changes use the `{submit}()` tool to indicate your work is done.
    """)

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=system_prompt,
        submit_prompt=submit_prompt,
    )

    on_continue_message = dedent(f"""
        Please consider if you need to make any further changes to the files you are responsible for.
        {
        ""
        if solo_agent
        else "If you think that your implementation depends on the changes that other engineers make "
        "to the files they are responsible for you can use the `wait()` tool to wait for them "
        "to complete their work. Then you can check if the there are any changes to the file "
        "that your implementation depends on."
    }
        If you believe you have completed {"" if solo_agent else "your part of"} the task or there are no meaningful 
        changes you can make please call the `{"{submit}"}()` tool.
    """)

    if test_tool_func is None:
        test_tool_func = create_run_tests_tool

    tools = [
        create_file_reader_tool(agent_id, read_access, working_dir=working_dir),
        create_grep_tool(agent_id, read_access, working_dir=working_dir),
        create_patch_tool(
            agent_id,
            write_access,
            working_dir=working_dir,
            # TODO provide task-level interface for selecting these
            # validators=[static_safety_check],
            # modifiers=[sanitize_content],
        ),
        create_list_files_and_directories_tool(agent_id, working_dir=working_dir),
        *([create_wait_tool(agent_id)] if not solo_agent else []),
        test_tool_func(agent_id, required_tests=required_tests, working_dir=working_dir),
    ]

    react_agent = custom_react_agent.react(
        name=agent_id,
        description=None,
        prompt=prompt,
        tools=tools,
        on_continue=on_continue_message,
        submit=create_done_tool(agent_id),
        attempts=attempts,
        message_filter=message_filter,
    )

    return react_agent


@agent
def create_bash_agent(
    agent_id: str,
    read_access: str | List[str],
    write_access: str | List[str],
    required_tests: List[str] | None = None,
    test_tool_func: Callable | None = None,
    working_dir: str | None = None,
    attempts: int | AgentAttempts = 1,
    message_filter: MessageFilter | None = None,
    solo_agent: bool = False,
) -> Agent:
    if isinstance(read_access, str):
        if read_access.upper() in ["ALL"]:
            read_access = None
        else:
            read_access = [read_access]

    if isinstance(write_access, str):
        if write_access.upper() in ["ALL"]:
            write_access = None
        else:
            write_access = [write_access]

    # TODO Improve prompts.
    system_prompt = dedent(f"""
        You are an expert software engineer working {
        "" if solo_agent else "collaboratively with other equally capable engineers"
    } to solve a coding task.
        You are interacting with a standard Ubuntu machine with bash commands and python tools. Your bash session is 
        NOT stateful, so all commands must be self-contained.
        Your objective is to modify the code in the file(s) assigned to you to solve the task.
        The repository code is already checked out to the current working directory.
        You do NOT need to change branches or commit the fix.
        You can modify {
        "all files in the repository." if write_access is None else "ONLY the following file(s) in the repository:"
    } 
        {"" if write_access is None else write_access}
        
        {
        ""
        if test_tool_func is None
        else "You can use the dedicated `run_tests()` tool to specifically run all the "
        "tests that are required for the task."
    }
        
        {
        ""
        if solo_agent
        else "You also have access to a `wait()` tool that allows you to wait for other engineers to "
        "make changes to their files in case your implementation depends on their part of "
        "the task."
    }

        {"" if solo_agent else "The other engineers have access to the same tools but with different file permissions."}

        Your objective is to modify the code in the file(s) you have access to in order to complete the task.
        {"Work collaboratively with the other engineers to complete the task." if not solo_agent else ""}
        {"" if write_access is None else "Remember, you have the permission to modify the files specified above."} 
    """)

    submit_prompt = dedent("""
        When you are satisfied with your changes use the `{submit}()` tool to indicate your work is done.
    """)

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=system_prompt,
        submit_prompt=submit_prompt,
    )

    on_continue_message = dedent(f"""
        Please consider if you need to make any further changes to the files you are responsible for.
        {
        ""
        if solo_agent
        else "If you think that your implementation depends on the changes that other engineers make "
        "to the files they are responsible for you can use the `wait()` tool to wait for them "
        "to complete their work. Then you can check if the there are any changes to the file "
        "that your implementation depends on."
    }
        If you believe you have completed {"" if solo_agent else "your part of"} the task or there are no meaningful 
        changes you can make please call the `{"{submit}"}()` tool.
    """)

    tools = [
        bash(timeout=180, user=agent_id),
        python(timeout=180, user=agent_id),
        *([create_wait_tool(agent_id)] if not solo_agent else []),
        *([test_tool_func(agent_id)] if test_tool_func is not None else []),
    ]

    react_agent = custom_react_agent.react(
        name=agent_id,
        description=None,
        prompt=prompt,
        tools=tools,
        on_continue=on_continue_message,
        submit=create_done_tool(agent_id),
        attempts=attempts,
        message_filter=message_filter,
    )

    return react_agent


@solver
def agent_collection_solver(
    agents_config: List[AgentConfig] | None = None,
    tools_type: Literal["custom", "bash"] = "custom",
    test_tool_func_type: str | None = None,
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState | AgentState:
        """A multi-agent system."""

        configs: list[AgentConfig] = agents_config or state.metadata["agents_config"]

        is_solo_agent = len(configs) == 1

        tasks = []
        for agent_config in configs:
            specific_message = agent_config.agent_specific_message
            keep_common_message = agent_config.keep_common_message

            if specific_message is not None:
                if keep_common_message:
                    modified_messages = state.messages + [ChatMessageUser(content=specific_message)]
                else:
                    modified_messages = state.messages[:-1] + [ChatMessageUser(content=specific_message)]
                agent_state = AgentState(messages=modified_messages)
            else:
                agent_state = state

            if test_tool_func_type is None:
                test_tool_func = create_run_tests_tool
            elif test_tool_func_type == "swe_bench":
                test_tool_func = partial(create_run_tests_tool_SWE_bench, state=state)
            else:
                raise ValueError(test_tool_func_type)

            if tools_type == "custom":
                tasks.append(
                    run(
                        create_agent(
                            agent_id=agent_config.id,
                            read_access=agent_config.read_access,
                            write_access=agent_config.write_access,
                            required_tests=agent_config.required_tests,
                            test_tool_func=test_tool_func,
                            message_filter=agent_config.message_filter,
                            solo_agent=is_solo_agent,
                        ),
                        agent_state,
                    )
                )
            elif tools_type == "bash":
                tasks.append(
                    run(
                        create_bash_agent(
                            agent_id=agent_config.id,
                            read_access=agent_config.read_access,
                            write_access=agent_config.write_access,
                            required_tests=agent_config.required_tests,
                            test_tool_func=test_tool_func,
                            message_filter=agent_config.message_filter,
                            solo_agent=is_solo_agent,
                        ),
                        agent_state,
                    )
                )

        agent_states = await asyncio.gather(*tasks)

        # TODO maybe find a way to merge these chronologically?
        for agent_state in agent_states:
            state.messages.extend(agent_state.messages)

        return state

    return solve
