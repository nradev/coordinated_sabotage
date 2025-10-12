# This is a simple extension of the inspect_ai react agent that allows passing a message_filter
# TODO request/propose this in the inspect project

from typing import Literal, Sequence

from inspect_ai._util._async import is_callable_coroutine
from inspect_ai._util.content import ContentText
from inspect_ai.agent._react import (
    react_no_submit,
    _prompt_to_system_message,
    _resolve_overflow,
    _agent_generate,
    _handle_overflow,
    _call_on_continue,
    _remove_submit_tool,
    _resolve_agent,
)
from inspect_ai.model._call_tools import execute_tools
from inspect_ai.model._chat_message import (
    ChatMessage,
    ChatMessageTool,
    ChatMessageUser,
)
from inspect_ai.model._model import Model
from inspect_ai.scorer._score import score
from inspect_ai.tool._mcp.connection import mcp_connection
from inspect_ai.tool._tool import Tool, ToolResult, ToolSource, tool
from inspect_ai.tool._tool_def import ToolDef

from inspect_ai.agent._agent import Agent, AgentState, agent
from inspect_ai.agent._filter import MessageFilter
from inspect_ai.agent._types import (
    DEFAULT_CONTINUE_PROMPT,
    AgentAttempts,
    AgentContinue,
    AgentPrompt,
    AgentSubmit,
)


@agent
def react(
    *,
    name: str | None = None,
    description: str | None = None,
    prompt: str | AgentPrompt | None = AgentPrompt(),
    tools: Sequence[Tool | ToolDef | ToolSource] | None = None,
    model: str | Model | Agent | None = None,
    attempts: int | AgentAttempts = 1,
    submit: AgentSubmit | bool | None = None,
    on_continue: str | AgentContinue | None = None,
    truncation: Literal["auto", "disabled"] | MessageFilter = "disabled",
    message_filter: MessageFilter | None = None,
) -> Agent:
    """Extensible ReAct agent based on the paper [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629).

    Provide a `name` and `description` for the agent if you plan on using it
    in a multi-agent system (this is so other agents can clearly identify
    its name and purpose). These fields are not required when using `react()`
    as a top-level solver.

    The agent runs a tool use loop until the model submits an answer using the
    `submit()` tool. Use `instructions` to tailor the agent's system message
    (the default `instructions` provides a basic ReAct prompt).

    Use the `attempts` option to enable additional submissions if the initial
    submission(s) are incorrect (by default, no additional attempts are permitted).

    By default, the model will be urged to continue if it fails to call
    a tool. Customise this behavior using the `on_continue` option.

    Args:
       name: Agent name (required when using with `handoff()` or `as_tool()`)
       description: Agent description (required when using with `handoff()` or `as_tool()`)
       prompt: Prompt for agent. Includes agent-specific contextual `instructions`
          as well as an optional `assistant_prompt` and `handoff_prompt` (for agents
          that use handoffs). both are provided by default but can be removed or
          customized). Pass `str` to specify the instructions and use the defaults
          for handoff and prompt messages.
       tools: Tools available for the agent.
       model: Model to use for agent (defaults to currently evaluated model).
       attempts: Configure agent to make multiple attempts.
       submit: Use a submit tool for reporting the final answer. Defaults to `True`
          which uses the default submit behavior. Pass an `AgentSubmit` to
          customize the behavior or pass `False` to disable the submit tool.
       on_continue: Message to play back to the model to urge it to continue
          when it stops calling tools. Use the placeholder {submit} to refer to
          the submit tool within the message. Alternatively, an async function
          to call to determine whether the loop should continue and what message
          to play back. Note that this function is called on _every_ iteration of
          the loop so if you only want to send a message back when the model fails
          to call tools you need to code that behavior explicitly.
       truncation: Truncate the conversation history in the event of a context
          window overflow. Defaults to "disabled" which does no truncation. Pass
          "auto" to use `trim_messages()` to reduce the context size. Pass a
          `MessageFilter` function to do custom truncation.
       message_filter: Optional `MessageFilter` function to apply after each model
          generation, allowing custom filtering or modification of the conversation
          history during the agent loop (applied independently of truncation).

    Returns:
        ReAct agent.
    """
    # if there is no submit tool then delegate to react_no_submit
    if submit is False:
        # if the user passes a `str` for on_continue this won't do anything
        if isinstance(on_continue, str):
            raise ValueError(
                "Passing a string to on_continue with no submit tool is not permitted, "
                + "because in this case the agent will always terminate when no tool "
                + "calls are made."
            )

        return react_no_submit(
            name=name,
            description=description,
            prompt=prompt,
            tools=tools,
            model=model,
            on_continue=on_continue,
            truncation=truncation,
        )

    # if submit is True or None then use default AgentSubmit
    if submit is True or submit is None:
        submit = AgentSubmit()

    # default submit tool
    @tool(name="submit")
    def default_submit_tool() -> Tool:
        async def execute(answer: str) -> ToolResult:
            """Submit an answer for evaluation.

            Args:
              answer (str): Submitted answer
            """
            return answer

        return execute

    # resolve tools
    tools = list(tools) if tools is not None else []

    # resolve submit tool
    submit_tool = (
        ToolDef(
            submit.tool or default_submit_tool(),
            name=submit.name,
            description=submit.description,
        )
        if not isinstance(submit.tool, ToolDef)
        else submit.tool
    )
    tools.append(submit_tool)

    # resolve prompt / system message
    system_message = _prompt_to_system_message(prompt, tools, submit_tool.name)

    # resolve attempts
    attempts = AgentAttempts(attempts) if isinstance(attempts, int) else attempts

    def submission(tool_results: list[ChatMessage]) -> str | None:
        return next(
            (
                result.text
                for result in tool_results
                if isinstance(result, ChatMessageTool)
                and result.function == submit_tool.name
                # Require that the submit tool call has no error
                and result.error is None
            ),
            None,
        )

    async def execute(state: AgentState) -> AgentState:
        async with mcp_connection(tools):
            # prepend system message if we have one
            if system_message:
                state.messages.insert(0, system_message)

            # resolve overflow handling
            overflow = _resolve_overflow(truncation)

            # track attempts
            attempt_count = 0

            # main loop = will terminate after submit (subject to max_attempts)
            # or if a message or token limit is hit
            while True:
                # generate output and append assistant message
                state = await _agent_generate(model, state, tools)

                # check for context window overflow
                if state.output.stop_reason == "model_length":
                    state, handled = await _handle_overflow(state, overflow)
                    if handled:
                        continue
                    else:
                        break

                if message_filter is not None:
                    state.messages = await message_filter(state.messages)

                # resolve tool calls (if any)
                if state.output.message.tool_calls:
                    # call tool functions
                    messages, output = await execute_tools(state.messages, tools)
                    state.messages.extend(messages)
                    if output:
                        state.output = output

                    # check for a submission
                    answer = submission(messages)
                    if answer is not None:
                        # set the output to the answer for scoring
                        if submit.answer_only:
                            state.output.completion = answer
                        else:
                            state.output.completion = (
                                f"{state.output.completion}{submit.answer_delimiter}{answer}".strip()
                            )

                        # also populate the message text (as the submit tool will be removed)
                        if not submit.keep_in_messages and len(state.output.choices) > 0:
                            message = state.output.choices[0].message
                            if isinstance(message.content, str):
                                message.content = f"{message.content}{submit.answer_delimiter}{answer}".strip()
                            else:
                                message.content.append(ContentText(text=answer))

                        # exit if we are at max_attempts
                        attempt_count += 1
                        if attempt_count >= attempts.attempts:
                            break

                        # exit if the submission is successful
                        answer_scores = await score(state)
                        if attempts.score_value(answer_scores[0].value) == 1.0:
                            break

                        # otherwise notify the model that it was incorrect and continue
                        else:
                            if callable(attempts.incorrect_message):
                                if not is_callable_coroutine(attempts.incorrect_message):
                                    raise ValueError("The incorrect_message function must be async.")
                                response_message: str = await attempts.incorrect_message(state, answer_scores)
                            else:
                                response_message = attempts.incorrect_message

                            state.messages.append(ChatMessageUser(content=response_message))

                # call the on_continue hook (if any)
                if callable(on_continue):
                    do_continue = await _call_on_continue(on_continue, state)
                    if do_continue is True:
                        # if there were no tool calls we need to send back a user message
                        if not state.output.message.tool_calls:
                            state.messages.append(
                                ChatMessageUser(content=DEFAULT_CONTINUE_PROMPT.format(submit=submit_tool.name))
                            )
                    elif isinstance(do_continue, str):
                        # send back the user message
                        state.messages.append(ChatMessageUser(content=do_continue.format(submit=submit_tool.name)))
                    else:  # do_continue is False
                        break

                # if there is no on_continue hook then add a user message if there were no tool calls
                elif not state.output.message.tool_calls:
                    continue_msg = DEFAULT_CONTINUE_PROMPT if on_continue is None else str(on_continue)
                    state.messages.append(ChatMessageUser(content=continue_msg.format(submit=submit_tool.name)))

            if not submit.keep_in_messages:
                # once we are complete, remove submit tool calls from the history
                # (as they will potentially confuse parent agents who also have
                # their own submit tools that they are 'watching' for)
                state.messages = _remove_submit_tool(state.messages, submit_tool.name)
            return state

    return _resolve_agent(execute, name, description)
