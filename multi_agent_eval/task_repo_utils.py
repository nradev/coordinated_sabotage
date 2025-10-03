"""
Repository utilities for SWE-bench tasks.

This module provides functions to clone and setup repositories at specific commits
for evaluation and testing purposes.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Union


def setup_task_repo(
    repo_info: Dict[str, str], target_dir: Optional[Union[str, Path]] = None, cleanup_on_error: bool = True
) -> Path:
    """
    Clone a GitHub repository and checkout to a specific commit.
    If the repository already exists, update it and checkout the commit.

    Args:
        repo_info: Dictionary containing 'repo' and 'base_commit' keys.
                  Example: {'repo': 'matplotlib/matplotlib', 'base_commit': '3dd06a46750d174f821df5377996f493f1af4ebb'}
        target_dir: Directory to clone into. If None, creates a temp directory.
        cleanup_on_error: If True, removes the directory if an error occurs.

    Returns:
        Path: Path to the repository directory

    Raises:
        ValueError: If repo_info is missing required keys
        subprocess.CalledProcessError: If git commands fail
        OSError: If directory operations fail
    """
    # Validate input
    if not isinstance(repo_info, dict):
        raise ValueError("repo_info must be a dictionary")

    required_keys = {"repo", "base_commit"}
    missing_keys = required_keys - set(repo_info.keys())
    if missing_keys:
        raise ValueError(f"repo_info missing required keys: {missing_keys}")

    repo = repo_info["repo"]
    commit = repo_info["base_commit"]

    # Validate repo format
    if "/" not in repo:
        raise ValueError(f"Invalid repo format: {repo}. Expected format: 'owner/repo'")

    # Create target directory
    if target_dir is None:
        target_dir = tempfile.mkdtemp(prefix=f"{repo.replace('/', '_')}_")
    else:
        target_dir = Path(target_dir)
        target_dir.mkdir(parents=True, exist_ok=True)

    target_path = Path(target_dir)
    repo_dir = target_path / repo.split("/")[-1]  # Use repo name as directory name

    try:
        # Check if repository already exists
        if repo_dir.exists() and (repo_dir / ".git").exists():
            print(f"Repository {repo} already exists, updating...")

            # Verify it's the correct repository
            try:
                result = subprocess.run(
                    ["git", "-C", str(repo_dir), "config", "--get", "remote.origin.url"],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                current_url = result.stdout.strip()
                expected_urls = [f"https://github.com/{repo}.git", f"git@github.com:{repo}.git"]

                if not any(current_url == url for url in expected_urls):
                    raise RuntimeError(f"Existing repository has different origin: {current_url}")

            except subprocess.CalledProcessError:
                raise RuntimeError("Existing directory is not a valid git repository")

            # Fetch latest changes
            print("Fetching latest changes...")
            subprocess.run(["git", "-C", str(repo_dir), "fetch", "--all"], check=True, capture_output=True, text=True)

        else:
            # Clone the repository
            if repo_dir.exists():
                print(f"Removing existing non-git directory at {repo_dir}")
                shutil.rmtree(repo_dir)

            # Construct GitHub URL
            github_url = f"https://github.com/{repo}.git"

            print(f"Cloning {repo} from GitHub...")
            subprocess.run(["git", "clone", github_url, str(repo_dir)], check=True, capture_output=True, text=True)

        # Reset to clean state and checkout specific commit
        print(f"Checking out commit {commit[:8]}...")

        # Clean any local changes
        subprocess.run(["git", "-C", str(repo_dir), "reset", "--hard"], check=True, capture_output=True, text=True)

        # Checkout the specific commit
        subprocess.run(["git", "-C", str(repo_dir), "checkout", commit], check=True, capture_output=True, text=True)

        # Verify we're at the correct commit
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        )

        current_commit = result.stdout.strip()
        if current_commit != commit:
            raise RuntimeError(f"Failed to checkout correct commit. Expected {commit}, got {current_commit}")

        print(f"Successfully setup {repo} at commit {commit[:8]}")
        return repo_dir

    except (subprocess.CalledProcessError, OSError, RuntimeError) as error:
        # Cleanup on error if requested
        if cleanup_on_error and repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        raise error


def get_repo_info(repo: str, commit: str) -> Dict[str, str]:
    """
    Helper function to create repo_info dictionary.

    Args:
        repo: Repository in format 'owner/repo'
        commit: Git commit hash

    Returns:
        Dict with 'repo' and 'base_commit' keys
    """
    return {"repo": repo, "base_commit": commit}


def cleanup_repo(repo_path: Union[str, Path]) -> None:
    """
    Remove a cloned repository directory.

    Args:
        repo_path: Path to the repository directory to remove
    """
    repo_path = Path(repo_path)
    if repo_path.exists():
        shutil.rmtree(repo_path, ignore_errors=True)
        print(f"Cleaned up repository at {repo_path}")


def validate_repo_state(repo_path: Union[str, Path], expected_commit: str) -> bool:
    """
    Validate that a repository is at the expected commit.

    Args:
        repo_path: Path to the repository directory
        expected_commit: Expected git commit hash

    Returns:
        bool: True if at expected commit, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"], check=True, capture_output=True, text=True
        )

        current_commit = result.stdout.strip()
        return current_commit == expected_commit

    except subprocess.CalledProcessError:
        return False


def is_git_repo(path: Union[str, Path]) -> bool:
    """
    Check if a path is a valid git repository.

    Args:
        path: Path to check

    Returns:
        bool: True if path is a git repository, False otherwise
    """
    path = Path(path)
    return path.exists() and (path / ".git").exists()


if __name__ == "__main__":
    # Example usage
    example_repo_info = {
        "repo": "octocat/Hello-World",
        "base_commit": "7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        # 'repo': 'matplotlib/matplotlib',
        # 'base_commit': '3dd06a46750d174f821df5377996f493f1af4ebb',
        # 'base_commit': '0849036fd992a2dd133a0cffc3f84f58ccf1840f'
    }

    try:
        repo_path = setup_task_repo(example_repo_info, target_dir="../tasks")
        print(f"Repository cloned to: {repo_path}")

        # Validate the setup
        if validate_repo_state(repo_path, example_repo_info["base_commit"]):
            print("Repository is at the correct commit")
        else:
            print("Repository is not at the expected commit")

    except Exception as e:
        print(f"Error: {e}")
