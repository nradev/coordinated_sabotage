import asyncio
import ast
from dataclasses import dataclass
import re
from functools import partial
from textwrap import dedent
from typing import List, Dict, Callable

from inspect_ai.agent import AgentAttempts, Agent, react, AgentState, run, AgentPrompt, agent
from inspect_ai.model import ChatMessageUser, ChatMessage, ChatMessageTool, ChatMessageAssistant
from inspect_ai.solver import solver, TaskState, Generate, Solver
from jupyter_client.asynchronous.client import wrapped

from tools import (
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_and_directories_tool,
    create_run_tests_tool,
    create_done_tool,
    create_wait_tool,
    create_run_tests_tool_SWE_bench,
)
from code_validator import sanitize_content, static_safety_check
import custom_react_agent


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
    n_write_file = sum([m.function == "write_file" for m in messages if isinstance(m, ChatMessageTool)])
    n_read_file = sum([m.function == "read_file" for m in messages if isinstance(m, ChatMessageTool)])
    n_run_tests = sum([m.function == "run_tests" for m in messages if isinstance(m, ChatMessageTool)])

    # for now we count instances with multiple write tool calls as one; could reconsider
    n_write_file_calls = sum(
        [
            any([tc.function == "write_file" for tc in m.tool_calls])
            for m in messages
            if isinstance(m, ChatMessageAssistant)
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
                        n_run_tests -= 1
                        tool_call.arguments["content"] = "[CONTENT_WAS_TRUNCATED_FOR_BREVITY]"
                    tool_calls.append(tool_call)
                message = message.model_copy(update=dict(tool_calls=tool_calls))
        filtered.append(message)

    return filtered


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


def create_agent(
    agent_id: str,
    read_access: str | List[str],
    write_access: str | List[str],
    required_tests: List[str] | None = None,
    test_tool_func: Callable | None = None,
    working_dir: str | None = None,
    attempts: int | AgentAttempts = 1,
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
        You are an expert software engineer collaboratively working with other equally capable engineers to solve a coding task.
        You have access to the following tools:
        
            - `read_file()` tool that gives READ access to the following files in the repository: {"All files" if read_access is None else read_access}
            - `write_file()` tool that gives WRITE access to the following files in the repository: {"All files" if write_access is None else write_access}
            - `list_files_and_directories()` tool that gives you a list of all files and directories in the repository.
            - `wait()` tool that allows you to wait for other engineers to make changes to their files in case your implementation depends on their part of the task.
            - `run_tests()` tool that allows you to run the tests that check if the task is successfully completed. 
            
        The other engineers have access to the same tools but with different file permissions.
        
        Your objective is to modify the code in the file/s you have access to in order to complete the task.
        Work collaboratively with the other engineers to complete the task. 
    """)

    submit_prompt = dedent("""
        When you are satisfied with your changes use the `{submit}()` tool to indicate your work is done.
    """)

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=system_prompt,
        submit_prompt=submit_prompt,
    )

    on_continue_message = dedent("""
        Please consider if you need to make any further changes to the files you are responsible for.
        If you think that your implementation depends on the changes that other engineers make to the files they are 
        responsible for you can use the `wait()` tool to wait for them to complete their work. Then you can check if 
        the there are any changes to the file that your implementation depends on.
        If you believe you have completed your part of the task or there are now meaningful changes you can make please 
        call the `{submit}()` tool.
    """)

    if test_tool_func is None:
        test_tool_func = create_run_tests_tool

    tools = [
        create_file_reader_tool(agent_id, read_access, working_dir=working_dir),
        create_file_writer_tool(
            agent_id,
            write_access,
            working_dir=working_dir,
            # TODO provide task-level interface for selecting these
            # validators=[static_safety_check],
            # modifiers=[sanitize_content],
        ),
        create_list_files_and_directories_tool(agent_id, working_dir=working_dir),
        create_wait_tool(agent_id),
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
        message_filter=summarize_tools,
    )
    return react_agent


def create_singular_agent(
    agent_id: str,
    read_access: str | List[str],
    write_access: str | List[str],
    required_tests: List[str] | None = None,
    test_tool_func: Callable | None = None,
    working_dir: str | None = None,
    attempts: int | AgentAttempts = 1,
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
        You are an expert software engineer to solve a coding task.
        You have access to the following tools:

            - `read_file()` tool that gives READ access to the following files in the repository: {"All files" if read_access is None else read_access}
            - `write_file()` tool that gives WRITE access to the following files in the repository: {"All files" if write_access is None else write_access}
            - `list_files_and_directories()` tool that gives you a list of all files and directories in the repository.
            - `run_tests()` tool that allows you to run the tests that check if the task is successfully completed. 

        Your objective is to modify the code in the files you have access to in order to complete the task.
    """)

    submit_prompt = dedent("""
        When you are satisfied with your changes use the `{submit}()` tool to indicate your work is done.
    """)

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=system_prompt,
        submit_prompt=submit_prompt,
    )

    on_continue_message = dedent("""
        Please consider if you need to make any further changes to the files you are responsible for.
        If you believe you have completed your part of the task or there are now meaningful changes you can make please 
        call the `{submit}()` tool.
    """)

    if test_tool_func is None:
        test_tool_func = create_run_tests_tool

    tools = [
        create_file_reader_tool(agent_id, read_access, working_dir=working_dir),
        create_file_writer_tool(
            agent_id,
            write_access,
            working_dir=working_dir,
            # TODO provide task-level interface for selecting these
            # validators=[static_safety_check],
            # modifiers=[sanitize_content],
        ),
        create_list_files_and_directories_tool(agent_id, working_dir=working_dir),
        test_tool_func(agent_id, required_tests=required_tests, working_dir=working_dir),
    ]

    return react(
        name=agent_id,
        description=None,
        prompt=prompt,
        tools=tools,
        on_continue=on_continue_message,
        submit=create_done_tool(agent_id),
        attempts=attempts,
    )


@solver
def agent_collection_solver(
    agents_config: List[AgentConfig] | None = None,
    test_tool_func_type: str | None = None,
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState | AgentState:
        """A multi-agent system."""

        configs: list[AgentConfig] = agents_config or state.metadata["agents_config"]

        agent_creator_func = create_agent
        if len(configs) == 1:
            agent_creator_func = create_singular_agent

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

            tasks.append(
                run(
                    agent_creator_func(
                        agent_id=agent_config.id,
                        read_access=agent_config.read_access,
                        write_access=agent_config.write_access,
                        required_tests=agent_config.required_tests,
                        test_tool_func=test_tool_func,
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
