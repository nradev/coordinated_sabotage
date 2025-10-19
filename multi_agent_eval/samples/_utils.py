from pathlib import Path


def scan_directory(task_dir: Path, workspace_name: str, file_filter=None):
    """Scan a task directory and return workspace-relative paths.

    Args:
        task_name: Name of the task directory under tasks/
        workspace_name: Name to use for workspace root
        file_filter: Optional callable to filter paths (receives Path object)

    Returns:
        List of workspace-relative Path objects
    """
    task_root = task_dir
    workspace_root = Path(workspace_name)

    # Get all files from the task directory
    all_task_files = list(task_root.rglob("*"))

    # Convert to workspace-relative paths
    workspace_files = []
    for file_path in all_task_files:
        if file_path.is_file():
            # Get relative path from task root and prepend workspace name
            rel_path = file_path.relative_to(task_root)
            workspace_path = workspace_root / rel_path

            # Apply filter if provided
            if file_filter is None or file_filter(workspace_path):
                workspace_files.append(workspace_path)

    return workspace_files
