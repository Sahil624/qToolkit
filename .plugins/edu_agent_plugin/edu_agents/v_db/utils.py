from pathlib import Path
import os


def singleton(cls):
    instances = {}  # Stores instances of decorated classes

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance


def find_project_root(marker_file=".project_root"):
    """
    Finds the project root by starting from the current working directory
    and searching upwards for a marker file.
    """
    # Start at the CWD (which is the notebook's directory)
    start_dir = Path(os.getcwd())
    current_dir = start_dir

    # Loop upwards until we hit the filesystem root
    while current_dir != current_dir.parent:
        if (current_dir / marker_file).exists():
            return current_dir  # Found it!
        current_dir = current_dir.parent

    # If we're at the root, check one last time
    if (current_dir / marker_file).exists():
        return current_dir

    # If we get here, the marker file was not found
    raise FileNotFoundError(
        f"Could not find project root. "
        f"Place a '{marker_file}' file in your project's root directory. "
        f"Started search from: {start_dir}"
    )