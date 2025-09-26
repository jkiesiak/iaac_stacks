import os

# Supported file extensions
SUPPORTED_EXTENSIONS = [".tf", ".json", ".py"]


def is_comment_line(line: str, extension: str) -> bool:
    """Check if a line is a comment based on file type."""
    stripped = line.strip()
    if not stripped:
        return False

    if extension == ".py":
        return stripped.startswith("#")
    elif extension == ".tf":
        return stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*")
    elif extension == ".json":
        # JSON technically doesn't have comments, but some tools allow "//"
        return stripped.startswith("//") or stripped.startswith("/*")
    return False


def count_lines_in_file(filepath: str) -> dict:
    """Count physical lines, blank lines, comments, and source lines for a single file."""
    extension = os.path.splitext(filepath)[1]
    if extension not in SUPPORTED_EXTENSIONS:
        return None

    total_lines = 0
    blank_lines = 0
    comment_lines = 0

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            total_lines += 1
            if not line.strip():
                blank_lines += 1
            elif is_comment_line(line, extension):
                comment_lines += 1

    sloc = total_lines - (blank_lines + comment_lines)  # Source Lines of Code
    ploc = total_lines  # Physical Lines of Code

    return {
        "file": filepath,
        "total": total_lines,
        "blank": blank_lines,
        "comments": comment_lines,
        "SLOC": sloc,
        "PLOC": ploc,
    }


def count_lines_in_directory(directory: str, excluded_folders: str = None):
    """Walk through a directory and count LOC for all supported files."""
    results = []
    total_summary = {"total": 0, "blank": 0, "comments": 0, "SLOC": 0, "PLOC": 0}

    for root, dirs, files in os.walk(directory):
        # Modify 'dirs' in-place to skip excluded folders
        dirs[:] = [d for d in dirs if d not in excluded_folders]

        for file in files:
            filepath = os.path.join(root, file)
            result = count_lines_in_file(filepath)
            if result:
                results.append(result)
                for key in total_summary:
                    if key in result:
                        total_summary[key] += result[key]

    return results, total_summary


if __name__ == "__main__":
    folder_path = "cdk_stack_infrastructure"
    excluded_folders = ".venv"
    output_file = "LOC_" + folder_path + ".txt"

    results, summary = count_lines_in_directory(folder_path, excluded_folders)

    # Print per-file results
    for r in results:
        print(f"{r['file']}: SLOC={r['SLOC']}, PLOC={r['PLOC']}, Comments={r['comments']}, Blank={r['blank']}")

    # Print summary
    print("\n--- Summary ---")
    print(f"Total Physical Lines of Code (PLOC): {summary['PLOC']}")
    print(f"Total Source Lines of Code (SLOC): {summary['SLOC']}")
    print(f"Total Comments: {summary['comments']}")
    print(f"Total Blank Lines: {summary['blank']}")
    # Build output string
    lines_out = []
    for r in results:
        lines_out.append(
            f"{r['file']}: SLOC={r['SLOC']}, PLOC={r['PLOC']}, Comments={r['comments']}, Blank={r['blank']}"
        )

    lines_out.append("\n--- Summary ---")
    lines_out.append(f"Total Physical Lines of Code (PLOC): {summary['PLOC']}")
    lines_out.append(f"Total Source Lines of Code (SLOC): {summary['SLOC']}")
    lines_out.append(f"Total Comments: {summary['comments']}")
    lines_out.append(f"Total Blank Lines: {summary['blank']}")

    output_text = "\n".join(lines_out)

    # Print to console
    print(output_text)

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"\nResults saved to {output_file}")