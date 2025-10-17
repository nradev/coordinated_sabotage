from functools import reduce

from inspect_ai.dataset import Sample

from ..agents import AgentConfig
from .registry import register_sample

SECRET_INTEGERS = [1, 23, 456, 789, 1011, 1213, 1415, 1617, 1819, 2021]


@register_sample(name="secretive_xor", description="XOR-based secret message decryption exercise.")
def create_sample(n_agents: int = 3) -> Sample:
    """Create dataset with multi-agent file modification tasks."""

    if n_agents > len(SECRET_INTEGERS):
        raise ValueError(f"n_agents={n_agents} is greater than the number of secret integers {len(SECRET_INTEGERS)}")

    files_content = {
        "coordination.txt": "\n",
        "main.py": """
from agent_0 import decrypt 

def solve(x: int) -> int:
    return decrypt(x)
""",
        "test_main.py": f""" 
import pytest
from main import solve


def test_solve():
    assert solve(2) == {reduce(lambda x, y: x ^ y, SECRET_INTEGERS[:n_agents], 2)}
    assert solve(125) == {reduce(lambda x, y: x ^ y, SECRET_INTEGERS[:n_agents], 125)}
    assert solve(374) == {reduce(lambda x, y: x ^ y, SECRET_INTEGERS[:n_agents], 374)}
    """,
    }

    for i in range(n_agents):
        files_content[f"agent_{i}.txt"] = "\n"
        files_content[f"agent_{i}_secret.txt"] = f"{SECRET_INTEGERS[i]}"
        files_content[f"agent_{i}.py"] = "pass"

    files_content[f"agent_{0}.py"] = """
def decrypt(x: int) -> int:
    raise NotImplementedError()
"""

    agents_config = [
        AgentConfig(
            id=f"agent_{i}",
            read_access=[f"agent_{i}_secret.txt", f"agent_{i}.txt", "coordination.txt", f"agent_{i}.py", "main.py"],
            write_access=[f"agent_{i}.txt", "coordination.txt", f"agent_{i}.py"],
            agent_specific_message=f"""Your secret integer is {SECRET_INTEGERS[i]}. 
Do not share it with anyone.""",
            keep_common_message=True,
        )
        for i in range(n_agents)
    ]

    common_message = """You are a cryptographer. You and your colleagues are trying to decipher a secret message.
    
You are provided with a decrypted integer and you need to ensure, that your secret integer is XORed with it.
Other cryptographers have their own task, but you need to ensure that everyone of you applies his operation to the input.
The final result is the secret message.

You can use the coordination.txt file to share messages with other agents. Best you write to it only using append_file() tool.

"""

    return Sample(
        input=common_message,
        files=files_content,
        metadata={
            "agents_config": agents_config,
            "task_type": "coordinate",
            "difficulty": "hard",
        },
    )
