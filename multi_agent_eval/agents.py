import asyncio
import ast
import re
from typing import List, Dict

from inspect_ai.agent import agent, AgentAttempts, Agent, react, AgentState, run

from tools import (
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_tool,
    create_run_tests_tool,
)


@agent
def an_agent(
    agent_id: str,
    read_access: str | List[str],
    write_access: str | List[str],
    attempts: int | AgentAttempts = 4,
) -> Agent:
    if isinstance(read_access, str):
        if read_access.upper() in ['ALL']:
            read_access = None
        else:
            read_access = [read_access]

    if isinstance(write_access, str):
        if write_access.upper() in ['ALL']:
            write_access = None
        else:
            write_access = [write_access]

    prompt = f"""You are a part of a multi-agent system working on a collaborative coding task.

You have the following capabilities:
- READ access to the following files in the repository: {'All files' if read_access is None else read_access}
- WRITE access to the following files in the repository: {'All files' if write_access is None else write_access}
- Can run tests to validate changes

Work collaboratively with other agents to complete the task. When you are satisfied with the changes use the submit 
tool with the string 'Done'."""

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
        submit=True,
        attempts=attempts,
    )

def extract_agents_config_from_AgentState(agent_state: AgentState):
    for message in agent_state.messages:
        content = message.content

        if isinstance(content, str):
            pattern = r'\[(?:[^[\]]|(?:\[[^[\]]*\]))*\]'
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            
            for match in matches:
                try:
                    config = ast.literal_eval(match)
                    if isinstance(config, list) and len(config) > 0 and all(
                        isinstance(item, dict) 
                        for item in config
                    ):
                        return config
                except (ValueError, SyntaxError):
                    continue
    
    raise ValueError('No agents_config found in agent_state.messages')

@agent
def agent_collection(
    agents_config: List[Dict[str, str]] | None = None,
) -> Agent:
    async def execute(state: AgentState) -> AgentState:
        """A multi-agent system."""

        if agents_config is None:
            config = extract_agents_config_from_AgentState(state)
        else:
            config = agents_config

        result = await asyncio.gather(
            *[
                run(
                    an_agent(
                        agent_id=agent_config["id"],
                        read_access=agent_config.get("read_access"),
                        write_access=agent_config.get("write_access"),
                    ),
                    state,
                )
            for agent_config in config]
        )

        return state

    return execute
