from pathlib import Path

from test_eval import create_sample_repo_files


def create_dockerfile_content() -> str:
    """Create Dockerfile content for the sandbox environment."""

    return '''FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \\
    git \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \\
    pytest \\
    pytest-asyncio \\
    pytest-cov

# Create workspace directory
WORKDIR /workspace

# Create directory for agent logs
RUN mkdir -p /workspace/.agent_logs

# Set up non-root user (optional but recommended)
RUN useradd -m -s /bin/bash agent && \\
    chown -R agent:agent /workspace

USER agent

# Keep container running
CMD ["tail", "-f", "/dev/null"]
'''


def create_compose_yaml() -> str:
    """Create docker-compose.yaml for the sandbox."""

    return '''version: '3.8'

services:
  default:
    build: .
    init: true
    working_dir: /workspace
    volumes:
      - ./workspace:/workspace
    environment:
      - PYTHONUNBUFFERED=1
    command: tail -f /dev/null
    mem_limit: 2g
    cpus: 2.0
    network_mode: bridge
'''


def setup_evaluation_environment(output_dir: Path = Path("multi_agent_eval")):
    """Set up the evaluation environment with necessary files."""

    output_dir.mkdir(exist_ok=True)

    # Create Dockerfile
    (output_dir / "Dockerfile").write_text(create_dockerfile_content())

    # Create compose.yaml
    (output_dir / "compose.yaml").write_text(create_compose_yaml())

    # Create workspace directory
    workspace_dir = output_dir / "workspace"
    workspace_dir.mkdir(exist_ok=True)

    # Create sample repository files
    for filename, content in create_sample_repo_files().items():
        (workspace_dir / filename).write_text(content)

    print(f"Evaluation environment created in {output_dir}")
    print(f"   - Dockerfile and compose.yaml created")
    print(f"   - Sample repository files created in workspace/")


if __name__ == "__main__":
    setup_evaluation_environment()
