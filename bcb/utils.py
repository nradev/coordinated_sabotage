import json
from pathlib import Path


def get_directory_files(directory_path):
    """
    Get all files in a directory and return their contents as a dictionary.

    Parameters:
    directory_path (str): Path to the directory (e.g., 'sample_42')

    Returns:
    dict: Dictionary where keys are file names and values are file contents as strings
    """
    directory = Path(directory_path)

    if not directory.exists():
        raise FileNotFoundError(f"Directory '{directory_path}' does not exist")

    if not directory.is_dir():
        raise NotADirectoryError(f"'{directory_path}' is not a directory")

    file_contents = {}

    for file_path in directory.iterdir():
        if file_path.is_file():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    file_contents[file_path.name] = f.read()
            except (UnicodeDecodeError, PermissionError) as e:
                # Skip files that cannot be read as text
                file_contents[file_path.name] = f"<Error reading file: {e}>"

    return file_contents


def write_directory_files_to_json(directory_path, output_path=None):
    """
    Write directory files contents to a JSON file.

    Parameters:
    directory_path (str): Path to the directory (e.g., 'sample_42')
    output_path (str, optional): Path for the output JSON file. If None, uses '{directory_path}_files.json'

    Returns:
    str: Path to the created JSON file
    """
    file_contents = get_directory_files(directory_path)

    if output_path is None:
        directory_name = Path(directory_path).name
        output_path = f"{directory_name}_files.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(file_contents, f, indent=2, ensure_ascii=False)

    return output_path


def write_multiple_directories_to_json(directory_paths, output_path="samples_files.json"):
    """
    Write multiple directories' files contents to a single JSON file.

    Parameters:
    directory_paths (list): List of directory paths (e.g., ['sample_42', 'sample_1'])
    output_path (str): Path for the output JSON file

    Returns:
    str: Path to the created JSON file
    """
    all_samples = {}

    for directory_path in directory_paths:
        try:
            file_contents = get_directory_files(directory_path)
            directory_name = Path(directory_path).name
            all_samples[directory_name] = file_contents
        except (FileNotFoundError, NotADirectoryError) as e:
            all_samples[Path(directory_path).name] = {"error": str(e)}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_samples, f, indent=2, ensure_ascii=False)

    return output_path


if __name__ == "__main__":
    json_path = write_multiple_directories_to_json(
        [
            "sample_42",
            "sample_42_base",
            "sample_95_base",
        ],
        output_path="samples_files.json",
    )
    print(f"Files written to: {json_path}")
