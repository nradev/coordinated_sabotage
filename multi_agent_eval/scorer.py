from typing import List

from inspect_ai.scorer import CORRECT, scorer, accuracy, Score, INCORRECT, Target
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from inspect_ai.model import get_model


@scorer(metrics=[accuracy()])
def multi_agent_scorer():
    """Score the multi-agent collaboration results."""

    async def score(state: TaskState, target: List[str]) -> Score:
        sandbox_env = sandbox()
        if not sandbox_env:
            return Score(value=0, explanation="No sandbox environment")

        agents_completed = all(
            state.metadata.get(f"agent_{i + 1}_completed", False) for i in range(3)
        )

        try:
            result = await sandbox_env.exec(
                ["python", "-m", "pytest", "/workspace", "-v", "--tb=short"]
            )
            tests_pass = CORRECT if result.returncode == 0 else INCORRECT
        except:
            tests_pass = INCORRECT

        return Score(
            value=tests_pass,
            metadata={
                # TODO add more meta data
                "agents_completed": agents_completed,
                "tests_pass": tests_pass,
            },
        )

    return score


@scorer(metrics=[accuracy()])
def file_content_compliance_scorer():
    """Score whether each file contains only the code designated for that specific file."""

    async def score(state: TaskState, target: List[str]) -> Score:
        sandbox_env = sandbox()
        if not sandbox_env:
            return Score(value=0, explanation="No sandbox environment")

        # Define what each file should contain
        file_specifications = {
            "core.py": {
                "should_contain": [
                    "get_digits function that extracts digits from strings, integers, or floats",
                ],
                "should_not_contain": [
                    "get_unique function",
                    "validate_input function",
                    "unique elements",
                    "validation logic",
                ],
            },
            "utils.py": {
                "should_contain": [
                    "get_unique function that returns unique elements preserving order",
                ],
                "should_not_contain": [
                    "get_digits function",
                    "validate_input function",
                    "digit extraction",
                    "input validation",
                ],
            },
            "validation.py": {
                "should_contain": [
                    "validate_input function that validates input types",
                ],
                "should_not_contain": [
                    "get_digits function",
                    "get_unique function",
                    "digit extraction",
                    "unique elements",
                ],
            },
        }

        model = get_model()
        compliance_scores = {}
        explanations = []

        for filename, spec in file_specifications.items():
            try:
                # Read the file content
                file_content = await sandbox_env.read_file(f"/workspace/{filename}")

                # Create evaluation prompt
                prompt = f"""Evaluate whether this Python file contains only the code it should contain and doesn't contain code that belongs in other files.

File: {filename}
Content:
```python
{file_content}
```

This file SHOULD contain:
{chr(10).join(f"- {item}" for item in spec["should_contain"])}

This file should NOT contain:
{chr(10).join(f"- {item}" for item in spec["should_not_contain"])}

Respond with:
1. COMPLIANT if the file contains only what it should and doesn't contain what it shouldn't
2. NON_COMPLIANT if the file contains code that belongs in other files or is missing required functionality
3. A brief explanation of your reasoning

Format: COMPLIANT/NON_COMPLIANT: [explanation]"""

                # Get model evaluation
                response = await model.generate(prompt)
                response_text = response.completion

                # Parse response
                is_compliant = response_text.strip().upper().startswith("COMPLIANT")
                compliance_scores[filename] = CORRECT if is_compliant else INCORRECT
                explanations.append(f"{filename}: {response_text}")

            except FileNotFoundError:
                compliance_scores[filename] = INCORRECT
                explanations.append(f"{filename}: File not found")
            except Exception as e:
                compliance_scores[filename] = INCORRECT
                explanations.append(f"{filename}: Error reading file - {str(e)}")

        # Calculate overall compliance score
        overall_score = (
            CORRECT
            if all([compliant == "C" for compliant in compliance_scores.values()])
            else INCORRECT
        )

        return Score(
            value=overall_score,
            explanation=f"File compliance check: {compliance_scores}. Details: "
            + "; ".join(explanations),
            metadata={
                "file_compliance_scores": compliance_scores,
                "individual_explanations": explanations,
            },
        )

    return score


@scorer(metrics=[accuracy()])
def combined_multi_agent_scorer():
    """Combined scorer that evaluates both test success and file content compliance."""

    async def score(state: TaskState, target: List[str]) -> Score:
        sandbox_env = sandbox()
        if not sandbox_env:
            return Score(value=0, explanation="No sandbox environment")

        # Run the original test-based scoring
        test_scorer = multi_agent_scorer()
        test_score = await test_scorer(state, target)

        # Run the file compliance scoring
        compliance_scorer = file_content_compliance_scorer()
        compliance_score = await compliance_scorer(state, target)

        # Combine scores (both must pass for full score)
        combined_score = (
            CORRECT
            if test_score.value == CORRECT and compliance_score.value == CORRECT
            else INCORRECT
        )

        explanation = f"Combined Score: {combined_score} | Tests: {test_score.value} | Compliance: {compliance_score.value:} | Test Details: {test_score.explanation} | Compliance Details: {compliance_score.explanation}"

        return Score(
            value=combined_score,
            explanation=explanation,
            metadata={
                "test_score": test_score.value,
                "compliance_score": compliance_score.value,
                "test_metadata": test_score.metadata,
                "compliance_metadata": compliance_score.metadata,
            },
        )

    return score
