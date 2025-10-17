from inspect_ai import eval
from multi_agent_eval.tasks import multi_agent_file_modification

# this can be used for debugging
if __name__ == "__main__":
    eval(
        tasks=multi_agent_file_modification,
        model="openai/gpt-4o-mini",
    )
