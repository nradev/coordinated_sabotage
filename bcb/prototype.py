import json
import sys
import warnings
from pathlib import Path
from pprint import pprint
from typing import Literal, Type, TypeAlias

from openai import OpenAI
from pydantic import BaseModel

openai_client = OpenAI()

Message: TypeAlias = dict[Literal["role", "content"], str]
Messages: TypeAlias = list[Message]


# @retry_with_exponential_backoff
def generate_structured_response(
    model: str,
    messages: Messages,
    response_format: Type,
    temperature: float = 1,
    max_tokens: int = 1000,
    stop_sequences: list[str] = [],
) -> dict:
    """
    Generate a response using the OpenAI or Anthropic APIs, with a particular response format.

    Args:
        model (str): The name of the model to use (e.g., "gpt-4o-mini").
        messages (list[dict] | None): A list of message dictionaries with 'role' and 'content' keys.
        response_format (Type): The class to use for the response format.
        temperature (float): Controls randomness in output. Higher values make output more random.
        max_tokens (int): The maximum number of tokens to generate.
        verbose (bool): If True, prints the input messages before making the API call.
        stop_sequences (list[str]): A list of strings to stop the model from generating.

    Returns:
        dict: The model's response, as a dict with the same structure as the `response_format` class
            we pass in.
    """
    if model not in ["gpt-4o-mini", "claude-3-5-sonnet-20240620"]:
        warnings.warn(f"Warning: using unexpected model {model!r}")

    try:
        if "gpt" in model:
            response = openai_client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stop=stop_sequences,
                response_format=response_format,
            )
            return json.loads(response.choices[0].message.content)
            # elif "claude" in model:
            #     # Extract system message if present
            #     has_system = messages[0]["role"] == "system"
            #     kwargs = {"system": messages[0]["content"]} if has_system else {}
            #     msgs = messages[1:] if has_system else messages
            #
            #     response = instructor.from_anthropic(client=anthropic_client).messages.create(
            #         model=model,
            #         messages=msgs,
            #         temperature=temperature,
            #         max_tokens=max_tokens,
            #         stop_sequences=stop_sequences,
            #         response_model=response_format,
            #         **kwargs,
            #     )
            return response.model_dump()
        else:
            raise ValueError(f"Unknown model {model!r}")

    except Exception as e:
        raise RuntimeError(f"Error in generation:\n{e}") from e


class Answers(BaseModel):
    A: str
    B: str


class Question(BaseModel):
    system: str
    question: str
    answers: Answers
    answer_matching_behavior: Literal["A", "B"]
    answer_not_matching_behavior: Literal["A", "B"]
    behavior_category: str


class QuestionGeneration(BaseModel):
    reasoning: str  # Allow model to do chain-of-thought reasoning before generating the questions
    questions: list[Question]  # List of questions, all formatted the same way


if __name__ == "__main__":
    response = generate_structured_response(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": "Generate 4 factual questions about France's culture.",
            }
        ],
        response_format=QuestionGeneration,
    )
    pprint(response, width=120, sort_dicts=False)
