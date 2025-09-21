import asyncio
import ast
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


def extract_agents_config_from_AgentState(agent_state: AgentState):
    for message in agent_state.messages:
        content = message.content

        if isinstance(content, str):
            pattern = r"\[(?:[^[\]]|(?:\[[^[\]]*\]))*\]"
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)

            for match in matches:
                try:
                    config = ast.literal_eval(match)
                    if isinstance(config, list) and len(config) > 0 and all(isinstance(item, dict) for item in config):
                        return config
                except (ValueError, SyntaxError):
                    continue

    raise ValueError("No agents_config found in agent_state.messages")


@solver
def agent_collection_solver(
    agents_config: List[Dict[str, str]] | None = None,
) -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState | AgentState:
        """A multi-agent system."""

        if agents_config is None:
            default_config = {"id": "single_agent", "read_access": "ALL", "write_access": "ALL"}
            config = state.metadata.get("agents_config", default_config)
        else:
            config = agents_config

        tasks = []
        for agent_config in config:
            agent_id = agent_config["id"]
            specific_message = agent_config.get("agent_specific_message")
            keep_common_message = agent_config.get("keep_common_message", True)

            if specific_message is not None:
                if keep_common_message:
                    modified_messages = state.messages + [ChatMessageUser(content=specific_message)]
                else:
                    modified_messages = state.messages[:-1] + [ChatMessageUser(content=specific_message)]
                agent_state = AgentState(messages=modified_messages)
            else:
                agent_state = state

            tasks.append(
                run(
                    create_agent(
                        agent_id=agent_id,
                        read_access=agent_config.get("read_access"),
                        write_access=agent_config.get("write_access"),
                    ),
                    agent_state,
                )
            )

        result = await asyncio.gather(*tasks)
        # TODO result is a List[AgentState]. Should we somehow merge and return it?

        return state

    return solve
