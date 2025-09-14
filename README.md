# Setup

Before using the code, you need to set up your API keys. Run the following commands in your terminal:

```bash
# For OpenAI
export OPENAI_API_KEY="your-api-key"

# For Anthropic
export ANTHROPIC_API_KEY="your-api-key"
```

Then you can run a simple evaluation:

```bash
inspect eval multi_agent_eval/test_eval.py --model anthropic/claude-3-opus
```

Evaluation results can be found in the `logs/` directory.

