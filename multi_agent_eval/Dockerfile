FROM python:3.11-slim

# Install required packages
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov

# Create workspace directory
WORKDIR /workspace

# Create directory for agent logs
RUN mkdir -p /workspace/.agent_logs

# Set up non-root user (optional but recommended)
RUN useradd -m -s /bin/bash agent && \
    chown -R agent:agent /workspace

USER agent

# Keep container running
CMD ["tail", "-f", "/dev/null"]
