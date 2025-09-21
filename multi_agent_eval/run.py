from inspect_ai import eval
from test_eval import multi_agent_file_modification

# this can be used for debugging
if __name__ == "__main__":
    eval(
        tasks=multi_agent_file_modification,
        model="openai/llama-4-scout-17b-16e-instruct",
    )
