import asyncio
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
    prompt = f"""You an agent part of a multi-agent system working on a collaborative coding task.

You have the following capabilities:
- READ access to ALL files in the repository
- WRITE access ONLY to: {allowed_file}
- Can run tests to validate changes

Work collaboratively with other agents to complete the task."""

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
        attempts=attempts,
    )


@agent
def agent_collection(
    agents_config: List[Dict[str, str]],
) -> Agent:
    async def execute(state: AgentState) -> AgentState:
        """A multi-agent system."""

        result = await asyncio.gather(
            *[
                run(
                    an_agent(
                        agent_id=config["id"],
                        allowed_file=config["file"],
                    ),
                    state,
                )
            for config in agents_config]
        )

        return state

    return execute
