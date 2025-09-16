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
    allowed_file: str,
    attempts: int | AgentAttempts = 4,
) -> Agent:
    prompt = f"""You are a part of a multi-agent system working on a collaborative coding task.

You have the following capabilities:
- READ access to ALL files in the repository
- WRITE access ONLY to: {allowed_file}
- Can run tests to validate changes

Work collaboratively with other agents to complete the task. When you are satisfied with the changes use the submit 
tool with the string 'Done'"""

    tools = [
        create_file_reader_tool(agent_id),
        create_file_writer_tool(agent_id, allowed_file),
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
            pattern = r'\[(?:\s*\{\s*["\']id["\']\s*:\s*["\'][^"\']*["\']\s*,\s*["\']file["\']\s*:\s*["\'][^"\']*["\']\s*\}\s*,?\s*)+\]'
            matches = re.findall(pattern, content, re.DOTALL | re.MULTILINE)
            
            for match in matches:
                try:
                    config = ast.literal_eval(match)
                    if isinstance(config, list) and all(
                        isinstance(item, dict) and "id" in item and "file" in item 
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
                        allowed_file=agent_config["file"],
                    ),
                    state,
                )
            for agent_config in config]
        )

        return state

    return execute
