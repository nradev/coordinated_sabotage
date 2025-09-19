from typing import List

from inspect_ai.scorer import scorer, accuracy, Score
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox


@scorer(metrics=[accuracy()])
def multi_agent_scorer():
    """Score the multi-agent collaboration results."""

    async def score(state: TaskState, target: List[str]) -> Score:
        sandbox_env = sandbox()
        if not sandbox_env:
            return Score(value=0, explanation="No sandbox environment")

        agents_completed = all(state.metadata.get(f"agent_{i + 1}_completed", False) for i in range(3))

        try:
            result = await sandbox_env.exec(["python", "-m", "pytest", "/workspace", "-v", "--tb=short"])
            tests_pass = result.returncode == 0
        except:
            tests_pass = False

        return Score(
            value=int(tests_pass),
            metadata={
                # TODO add more meta data
                "agents_completed": agents_completed,
                "tests_pass": tests_pass,
            },
        )

    return score
