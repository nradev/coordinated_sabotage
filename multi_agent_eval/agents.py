import asyncio
import ast
from dataclasses import dataclass
import re
from typing import List, Dict

from inspect_ai.agent import AgentAttempts, Agent, react, AgentState, run, AgentPrompt
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import solver, TaskState, Generate, Solver

from tools import (
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_tool,
    create_run_tests_tool,
    create_done_tool,
)


@dataclass
class AgentConfig:
    """Configuration for an agent."""

    id: str
    read_access: str | list[str]
    """Path to file or directory to read from. Use 'ALL' to read from all files."""
    write_access: str | list[str]
    """Path to file or directory to write to. Use 'ALL' to write to all files."""
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

    assistant_prompt = f"""You are a part of a multi-agent system working on a collaborative coding task.

You have the following capabilities:
- READ access to the following files in the repository: {"All files" if read_access is None else read_access}
- WRITE access to the following files in the repository: {"All files" if write_access is None else write_access}
- Can run tests to validate changes

Work collaboratively with other agents to complete the task. """

    submit_prompt = """When you are satisfied with your changes use the `{submit}()` 
tool to indicate your work is done."""

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=assistant_prompt,
        submit_prompt=submit_prompt,
    )

    nudge_message = """Please consider if you need to make any further changes to the files you are responsible for. 
If you believe you have completed your part of the task, please call the `{submit}()`."""

    tools = [
        create_file_reader_tool(agent_id, read_access),
        create_file_writer_tool(agent_id, write_access),
        create_list_files_tool(agent_id),
        create_run_tests_tool(agent_id),
    ]

    return react(
        name=agent_id,
        description="An agent",
        prompt=prompt,
        tools=tools,
        on_continue=nudge_message,
        submit=create_done_tool(agent_id),
        attempts=attempts,
    )


@solver
def agent_collection_solver(
    agents_config: List[AgentConfig] | None = None,
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState | AgentState:
        """A multi-agent system."""

        configs: list[AgentConfig] = agents_config or state.metadata["agents_config"]

        tasks = []
        for agent_config in configs:
            specific_message = agent_config.agent_specific_message
            keep_common_message = agent_config.keep_common_message

            if specific_message is not None:
                if keep_common_message:
                    modified_messages = state.messages + [
                        ChatMessageUser(content=specific_message)
                    ]
                else:
                    modified_messages = state.messages[:-1] + [
                        ChatMessageUser(content=specific_message)
                    ]
                agent_state = AgentState(messages=modified_messages)
            else:
                agent_state = state

            tasks.append(
                run(
                    create_agent(
                        agent_id=agent_config.id,
                        read_access=agent_config.read_access,
                        write_access=agent_config.write_access,
                    ),
                    agent_state,
                )
            )

        result = await asyncio.gather(*tasks)
        # TODO result is a List[AgentState]. Should we somehow merge and return it?

        return state

    return solve
