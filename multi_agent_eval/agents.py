import asyncio
import ast
from dataclasses import dataclass
import pprint
import re
from typing import List, Dict

from inspect_ai.agent import AgentAttempts, Agent, agent, react, AgentState, run, AgentPrompt
from inspect_ai.model import ChatMessageSystem, ChatMessageUser, execute_tools, get_model
from inspect_ai.solver import solver, TaskState, Generate, Solver
from inspect_ai.util import sandbox
from loguru import logger

from tools import (
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_tool,
    create_run_tests_tool,
    create_done_tool,
    create_wait_tool,
)
from code_validator import sanitize_content, static_safety_check


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

    # TODO Improve prompts.
    assistant_prompt = f"""You are a part of a multi-agent system working on a collaborative coding task.

You have the following capabilities:
- `read_file()` tool that gives READ access to the following files in the repository: {"All files" if read_access is None else read_access}
- `write_file()` tool that gives WRITE access to the following files in the repository: {"All files" if write_access is None else write_access}
- `list_files()` tool that gives you a list of all Python files in the repository.
- `wait()` tool that allows you to wait for other agents to make changes to their files in case your implementation depends on their part of the task .
- `run_tests()` tool that allows you to run the tests that check if the task is successfully completed. 

Work collaboratively with other agents to complete the task. """

    submit_prompt = """When you are satisfied with your changes use the `{submit}()` 
tool to indicate your work is done."""

    prompt = AgentPrompt(
        instructions=None,
        assistant_prompt=assistant_prompt,
        submit_prompt=submit_prompt,
    )

    on_continue_message = """Please consider if you need to make any further changes to the files you are responsible for.
If you think that your implementation depends on the changes that other agents make to the files they are responsible for
 you can use the `wait()` tool to wait for them to complete their work. Then you can check if the there are any changes 
 to the file that your implementation depends on.
If you believe you have completed your part of the task, please call the `{submit}()` tool."""

    tools = [
        create_file_reader_tool(agent_id, read_access),
        create_file_writer_tool(
            agent_id,
            write_access,
            # TODO provide task-level interface for selecting these
            # validators=[static_safety_check],
            # modifiers=[sanitize_content],
        ),
        create_list_files_tool(agent_id),
        create_wait_tool(agent_id),
        create_run_tests_tool(agent_id),
    ]

    return react(
        name=agent_id,
        description="An agent",
        prompt=prompt,
        tools=tools,
        on_continue=on_continue_message,
        submit=create_done_tool(agent_id),
        attempts=attempts,
    )


@agent(name="forgetful_agent", description="A forgetful agent that does not remember its conversation history.")
def forgetful_agent() -> Agent:
    """A forgetful agent that does not remember its conversation history.

    This agent is a baseline for the multi-agent evaluation. It always receives the full project state and is given one
    write action.

    TODO:
    - [ ] tune pytest output signal
    """

    async def execute(state: AgentState) -> AgentState:
        while True:
            # clear the conversation history
            # We keep the first message, which is the system prompt
            state.messages = state.messages[:1]

            state.messages.append(
                ChatMessageSystem(
                    content=f"""
You are a Senior Software Engineer working on a Python codebase.

You have the following capabilities:
- `write_file()` tool: this tool allows you to write to a single file in the codebase.

Do some reasoning before your actions, describing what tool calls you are going to use and how they fit into your plan.

When all tests are passing and you are satisfied with your changes use the `submit()` tool to indicate your work is done.

Every round you can only do one action: either a single tool call or a `submit()` tool call.
"""
                )
            )

            state.messages.append(ChatMessageUser(content=await get_project_state(state)))

            tools = [
                create_file_writer_tool(
                    "agent_0",
                    None,
                )
            ]

            output = await get_model().generate(state.messages, tools)
            logger.debug(f"Agent 0: {output.message}")
            state.messages.append(output.message)

            if output.message.tool_calls:
                # trim tool calls to only the first one
                output.message.tool_calls = output.message.tool_calls[:1]

                messages, output = await execute_tools(state.messages, tools)
                state.messages.extend(messages)
                state.output = output
            else:
                # break on no tool calls. Alternatively we could check for submit and continue until then
                break
        return state

    return execute


async def get_project_state(agent_state: AgentState) -> bool | str:
    env = sandbox()

    result = await env.exec(["find", f"/workspace/", "-name", "*.py", "-type", "f"])

    contents = {}
    for file in result.stdout.strip().split("\n"):
        contents[file.replace("/workspace/", "")] = await env.read_file(file)

    test_results = await env.exec(["python", "-m", "pytest", f"/workspace/", "-q", "--tb=line"])
    test_results = test_results.stdout.strip().split("\n")[-1]

    project_state = f"""Remember, you are given one write action, then your state will be reset.

The current project state is 
{pprint.pformat(contents)}

The current test results are:
{test_results}

If you are satisfied with the current state, you can call the `submit()` tool.
"""
    logger.debug(project_state)
    return project_state


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
                    modified_messages = state.messages + [ChatMessageUser(content=specific_message)]
                else:
                    modified_messages = state.messages[:-1] + [ChatMessageUser(content=specific_message)]
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

        agent_states = await asyncio.gather(*tasks)

        # TODO maybe find a way to merge these chronologically?
        for agent_state in agent_states:
            state.messages.extend(agent_state.messages)

        return state

    return solve
