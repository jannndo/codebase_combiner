import os
import sys
import argparse
from typing import List, Tuple, Set


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Combine project files into a single file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Combine all Python files:
  combiner.py /path/to/project output.txt -f .py

  # Combine Python and C++ files:
  combiner.py /path/to/project output.txt -f .py .cpp

  # Combine all files and generate separate tree:
  combiner.py /path/to/project output.txt -st

  # Exclude specific directories and files:
  combiner.py /path/to/project output.txt -e venv build dist config.ini .env
        """,
    )
    parser.add_argument("project_path", help="Path to the project directory")
    parser.add_argument("output_file", help="Output file name")
    parser.add_argument(
        "-f",
        "--file-types",
        nargs="+",
        help="File extensions to include (e.g., .py .cpp .h). If not specified, includes all files",
    )
    parser.add_argument(
        "-e",
        "--exclude",
        nargs="+",
        default=["venv", "__pycache__", "resources", ".git", ".gitignore"],
        help="Directories and files to exclude (default: venv __pycache__ .git .gitignore)",
    )
    parser.add_argument(
        "-st",
        "--separate-tree",
        action="store_true",
        help="Generate tree structure in a separate file",
    )
    return parser.parse_args()


def should_skip_path(path: str, exclude_items: Set[str]) -> bool:
    """Check if path should be skipped based on excluded items"""
    path_parts = path.split(os.sep)
    return any(excluded in path_parts for excluded in exclude_items)


def should_skip_file(filename: str, exclude_items: Set[str]) -> bool:
    """Check if file should be skipped based on excluded items"""
    return filename in exclude_items


def is_included_file(filename: str, file_types: Set[str]) -> bool:
    """Check if file should be included based on its extension"""
    if not file_types:  # If no file types specified, include all files
        return True
    return any(filename.endswith(ext) for ext in file_types)


def scan_directory(
    path: str, exclude_items: Set[str], file_types: Set[str]
) -> List[Tuple[str, str]]:
    """
    Scan directory and return list of (file_path, relative_path) tuples,
    excluding specified directories and files, and filtering by file types
    """
    file_paths = []
    for root, _, files in os.walk(path):
        # Skip excluded directories
        if should_skip_path(root, exclude_items):
            continue

        for file in files:
            # Skip excluded files and check file type
            if not should_skip_file(file, exclude_items) and is_included_file(
                file, file_types
            ):
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, path)
                file_paths.append((abs_path, rel_path))
    return sorted(file_paths)


def generate_tree(
    path: str, exclude_items: Set[str], file_types: Set[str]
) -> List[str]:
    """
    Generate tree structure similar to tree command,
    excluding specified directories and files, and showing file types
    """
    tree_output = [f"Directory structure of: {path}"]

    def add_to_tree(dir_path: str, prefix: str = ""):
        try:
            entries = os.listdir(dir_path)
        except PermissionError:
            return

        entries = sorted(entries)

        # Filter out excluded directories, files, and non-matching files
        filtered_entries = []
        for entry in entries:
            full_path = os.path.join(dir_path, entry)
            if os.path.isdir(full_path):
                if not should_skip_path(full_path, exclude_items):
                    filtered_entries.append(entry)
            elif not should_skip_file(entry, exclude_items) and is_included_file(
                entry, file_types
            ):
                filtered_entries.append(entry)

        for i, entry in enumerate(filtered_entries):
            is_last = i == len(filtered_entries) - 1
            current = os.path.join(dir_path, entry)

            if is_last:
                tree_output.append(f"{prefix}└── {entry}")
                new_prefix = prefix + "    "
            else:
                tree_output.append(f"{prefix}├── {entry}")
                new_prefix = prefix + "│   "

            if os.path.isdir(current):
                add_to_tree(current, new_prefix)

    add_to_tree(path)
    return tree_output


def combine_files(
    file_paths: List[Tuple[str, str]],
    project_path: str,
    tree_content: List[str],
    exclude_items: Set[str],
    file_types: Set[str],
    include_tree: bool = True,
) -> str:
    """
    Combine all files with their location comments and optionally include tree structure
    """
    combined_content = [
        "# Combined Project Files",
        f"# Project Path: {project_path}",
        "# Generated by ProjectCombiner",
        "#",
        "# Excluded items (directories and files):",
        f"# {', '.join(exclude_items) if exclude_items else 'None'}",
        "#",
        "# Included file types:",
        f"# {', '.join(file_types) if file_types else 'All files'}",
    ]

    if include_tree:
        # Add tree structure as comments
        combined_content.extend(["#", "# Project Structure:", "#"])
        combined_content.extend(f"# {line}" for line in tree_content)
        combined_content.extend(["#", "# File Contents:", "#"])

    # Add all files
    for abs_path, rel_path in file_paths:
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Add file separator and path information
            combined_content.extend(
                [
                    "#" * 80,
                    f"# File: {rel_path}",
                    "#" * 80,
                    content,
                    "\n",  # Add newline between files
                ]
            )
        except Exception as e:
            print(f"Warning: Error reading {abs_path}: {e}")
            continue

    return "\n".join(combined_content)


def main():
    # Parse command line arguments
    args = parse_args()
    project_path = os.path.abspath(args.project_path)
    output_file = args.output_file
    exclude_items = set(args.exclude)
    separate_tree = args.separate_tree
    file_types = set(args.file_types) if args.file_types else set()

    # Print configuration
    print(f"\nConfiguration:")
    print(f"Project path: {project_path}")
    print(f"Output file: {output_file}")
    print(f"File types: {', '.join(file_types) if file_types else 'All files'}")
    print(f"Excluded items: {', '.join(exclude_items)}")
    print(f"Separate tree file: {separate_tree}\n")

    # Ensure project path exists
    if not os.path.exists(project_path):
        print(f"Error: Path {project_path} does not exist")
        sys.exit(1)

    # Generate tree structure
    print("Generating directory tree...")
    tree_content = generate_tree(project_path, exclude_items, file_types)

    # Save tree to separate file if requested
    if separate_tree:
        tree_file = output_file.rsplit(".", 1)[0] + "_tree.txt"
        with open(tree_file, "w", encoding="utf-8") as f:
            f.write("\n".join(tree_content))
        print(f"Directory tree saved to: {tree_file}")

    # Scan for files
    print("Scanning for files...")
    file_paths = scan_directory(project_path, exclude_items, file_types)

    if not file_paths:
        print("Warning: No matching files found!")
        sys.exit(1)

    # Combine files
    print("Combining files...")
    combined_content = combine_files(
        file_paths,
        project_path,
        tree_content,
        exclude_items,
        file_types,
        not separate_tree,  # Include tree in combined file only if not separate
    )

    # Save combined content
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(combined_content)
        print(f"\nProcessed {len(file_paths)} files")
        print(f"Combined content saved to: {output_file}")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
