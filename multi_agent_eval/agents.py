import asyncio
from dataclasses import dataclass
from typing import Callable, Dict, List

from inspect_ai.agent import Agent, AgentAttempts, AgentPrompt, AgentState, react, run
from inspect_ai.model import ChatMessageUser
from inspect_ai.solver import Generate, Solver, TaskState, solver

from .tools import (
    create_done_tool,
    create_file_reader_tool,
    create_file_writer_tool,
    create_list_files_tool,
    create_run_tests_tool,
    create_wait_tool,
)


@dataclass(frozen=True)
class RegisteredSolver:
    name: str
    factory: Callable[[int], Solver]
    description: str


def _build_agent_collection_solver(max_messages: int) -> Solver:
    # The agent collection solver already returns a Solver via the decorator.
    return agent_collection_solver()


SOLVERS: Dict[str, RegisteredSolver] = {
    "multi": RegisteredSolver(
        name="multi",
        factory=_build_agent_collection_solver,
        description="Multi-agent collaborative solver.",
    ),
}


def get_solver(name: str, *, max_messages: int) -> Solver:
    """Return a solver instance registered under ``name``."""
    try:
        registered = SOLVERS[name]
    except KeyError as exc:
        available = ", ".join(sorted(SOLVERS))
        raise KeyError(f"Unknown solver '{name}'. Available solvers: {available}") from exc
    return registered.factory(max_messages)


def list_solvers() -> List[RegisteredSolver]:
    """Expose registered solvers for discovery."""
    return list(SOLVERS.values())


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
