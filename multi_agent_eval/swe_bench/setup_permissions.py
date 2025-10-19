"""Setup file permissions in Docker containers for restricted write access."""

import logging
import os
import tempfile
from typing import TYPE_CHECKING

from multi_agent_eval.environment.agents import AgentConfig

if TYPE_CHECKING:
    from docker.client import DockerClient

logger = logging.getLogger(__name__)


def setup_file_permissions(
    docker_client: "DockerClient",
    image_name: str,
    agent_configs: list[AgentConfig],
    working_dir: str = "/testbed",
) -> str:
    """
    Create a new Docker image with multiple users, each with restricted write permissions.

    This function takes a base Docker image and creates a new image where:
    1. Multiple non-root users are created, one per agent config
    2. Each user's ID corresponds to their agent ID
    3. Each user has write access only to files specified in their config

    This allows using general bash tools (like inspect_ai.tool.bash) while enforcing
    write restrictions at the filesystem level, similar to how create_file_writer_tool
    enforces restrictions at the tool level.

    Args:
        docker_client: Docker client instance
        image_name: Base image to modify
        agent_configs: List of agent configurations, each with id and write_access settings
        working_dir: Working directory in the container (default: /testbed)

    Returns:
        Name of the new restricted image

    Example:
        >>> from docker.client import DockerClient
        >>> from multi_agent_eval.environment.agents import AgentConfig
        >>> client = DockerClient.from_env()
        >>> configs = [
        ...     AgentConfig(id="agent1", read_access="ALL", write_access=["django/core/handlers.py"]),
        ...     AgentConfig(id="agent2", read_access="ALL", write_access=["django/core/views.py"]),
        ... ]
        >>> restricted_image = setup_file_permissions(
        ...     client,
        ...     "django__django-12345:latest",
        ...     configs,
        ...     working_dir="/testbed"
        ... )
        >>> # Use restricted_image for sandboxes, specifying user when running containers
    """
    # Build Dockerfile commands for each agent
    user_creation_commands = []
    permission_commands = []

    # Start from a higher UID to avoid conflicts with existing users
    for idx, agent_config in enumerate(agent_configs):
        uid = 5000 + idx  # Use UIDs starting from 5000 to avoid conflicts
        agent_id = agent_config.id
        write_access = agent_config.write_access

        # Parse write_access
        if isinstance(write_access, str):
            if write_access.upper() == "ALL":
                # Skip restrictions for this user - give full ownership
                user_creation_commands.append(f"RUN useradd -m -u {uid} {agent_id} || true")
                user_creation_commands.append(f"RUN chown -R {agent_id}:{agent_id} {working_dir}")
                logger.info(f"Agent {agent_id} has unrestricted write access")
                continue
            else:
                writable_files = [write_access]
        else:
            writable_files = write_access

        # Create user and set up group ownership (|| true to handle if user exists)
        user_creation_commands.append(f"RUN useradd -m -u {uid} {agent_id} || true")

        # Add user to a shared group for read access
        user_creation_commands.append(f"RUN usermod -a -G shared {agent_id} || true")

        # Set write permissions for this user's files
        for file_path in writable_files:
            full_path = f"{working_dir}/{file_path}"
            # Make the file owned by this user (only if file exists)
            permission_commands.append(
                f"RUN if [ -f {full_path} ]; then chown {agent_id}:shared {full_path} && chmod 664 {full_path}; fi"
            )

    # Build the Dockerfile
    dockerfile_content = f"""FROM {image_name}

# Create a shared group for all agents
RUN groupadd -g 2000 shared || true

# Create all agent users
{chr(10).join(user_creation_commands)}

# Set base ownership - make everything owned by root:shared
RUN chown -R root:shared {working_dir} || true

# Make directories readable/executable by all, writable only by root
RUN find {working_dir} -type d -exec chmod 755 {{}} \\; || true

# Make files readable by all, preserve execute bit, but writable only by root
# This removes write permission for group and others while preserving execute
RUN find {working_dir} -type f -exec chmod a-w,a+r {{}} \\; || true

# Set specific write permissions for each agent's files
{chr(10).join(permission_commands)}

# Don't switch to non-root user by default - let the bash tool specify the user
# This allows environment setup and test commands to run as root with full permissions
WORKDIR {working_dir}
"""

    # Build the restricted image
    with tempfile.TemporaryDirectory() as tmpdir:
        dockerfile_path = os.path.join(tmpdir, "Dockerfile")
        with open(dockerfile_path, "w") as f:
            f.write(dockerfile_content)

        restricted_image_name = f"{image_name}-multiagent"

        logger.info(f"Building restricted multi-agent image {restricted_image_name} from {image_name}")
        logger.debug(f"Agents: {[config.id for config in agent_configs]}")
        logger.debug(f"Dockerfile:\n{dockerfile_content}")

        try:
            docker_client.images.build(
                path=tmpdir,
                tag=restricted_image_name,
                rm=True,
            )
        except Exception as e:
            logger.error(f"Failed to build Docker image: {e}")
            logger.error(f"Dockerfile content:\n{dockerfile_content}")
            raise

        logger.info(f"Successfully built restricted image {restricted_image_name}")

    return restricted_image_name
