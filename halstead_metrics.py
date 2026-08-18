import os
import math
import re
import json
from collections import Counter
from typing import Dict, List, Tuple, Set

# Supported file extensions
SUPPORTED_EXTENSIONS = [".tf", ".json", ".py"]

# Define operators and keywords for each language
PYTHON_OPERATORS = {
    '+', '-', '*', '/', '//', '%', '**', '=', '+=', '-=', '*=', '/=', '//=', '%=', '**=',
    '==', '!=', '<', '>', '<=', '>=', 'and', 'or', 'not', 'is', 'in', 'not in',
    '&', '|', '^', '~', '<<', '>>', '&=', '|=', '^=', '<<=', '>>=',
    'if', 'elif', 'else', 'for', 'while', 'break', 'continue', 'def', 'class',
    'return', 'yield', 'import', 'from', 'as', 'try', 'except', 'finally',
    'raise', 'with', 'assert', 'pass', 'del', 'global', 'nonlocal', 'lambda'
}

TERRAFORM_OPERATORS = {
    '=', '!=', '<', '>', '<=', '>=', '&&', '||', '!', '+', '-', '*', '/', '%',
    'resource', 'data', 'variable', 'output', 'locals', 'module', 'provider',
    'terraform', 'for', 'if', 'else', 'for_each', 'count', 'depends_on',
    'lifecycle', 'provisioner', 'connection'
}

JSON_OPERATORS = {
    '{', '}', '[', ']', ':', ',', 'null', 'true', 'false'
}


class HalsteadAnalyzer:
    """Analyzer for calculating Halstead metrics for different file types."""

    def __init__(self, file_extension: str):
        self.extension = file_extension
        self.operators = self._get_operators()

    def _get_operators(self) -> Set[str]:
        """Get operators set based on file extension."""
        if self.extension == ".py":
            return PYTHON_OPERATORS
        elif self.extension == ".tf":
            return TERRAFORM_OPERATORS
        elif self.extension == ".json":
            return JSON_OPERATORS
        return set()

    def analyze_content(self, content: str) -> Tuple[int, int, int, int]:
        """
        Analyze content and return Halstead metrics.
        Returns: (unique_operators, unique_operands, total_operators, total_operands)
        """
        if self.extension == ".py":
            return self._analyze_python(content)
        elif self.extension == ".tf":
            return self._analyze_terraform(content)
        elif self.extension == ".json":
            return self._analyze_json(content)
        return 0, 0, 0, 0

    def _analyze_python(self, content: str) -> Tuple[int, int, int, int]:
        """Analyze Python code for Halstead metrics."""
        # Remove comments and strings to avoid false positives
        content = self._remove_python_comments_and_strings(content)

        # Tokenize the content
        tokens = re.findall(r'\b\w+\b|[+\-*/=<>!&|^~%]+|[(){}[\],.:;]', content)

        operators = []
        operands = []

        for token in tokens:
            if token in self.operators or self._is_python_operator(token):
                operators.append(token)
            elif token and not token.isspace():
                # Consider identifiers, numbers, and literals as operands
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', token) or re.match(r'^\d+(\.\d+)?$', token):
                    operands.append(token)

        unique_operators = len(set(operators))
        unique_operands = len(set(operands))
        total_operators = len(operators)
        total_operands = len(operands)

        return unique_operators, unique_operands, total_operators, total_operands

    def _analyze_terraform(self, content: str) -> Tuple[int, int, int, int]:
        """Analyze Terraform code for Halstead metrics."""
        # Remove comments
        content = self._remove_terraform_comments(content)

        # Tokenize
        tokens = re.findall(r'\b\w+\b|[=!<>]+|[{}[\](),.]', content)

        operators = []
        operands = []

        for token in tokens:
            if token in self.operators:
                operators.append(token)
            elif token and re.match(r'^[a-zA-Z_][a-zA-Z0-9_-]*$', token):
                operands.append(token)
            elif re.match(r'^".*"$', token) or re.match(r'^\d+(\.\d+)?$', token):
                operands.append(token)

        unique_operators = len(set(operators))
        unique_operands = len(set(operands))
        total_operators = len(operators)
        total_operands = len(operands)

        return unique_operators, unique_operands, total_operators, total_operands

    def _analyze_json(self, content: str) -> Tuple[int, int, int, int]:
        """Analyze JSON for Halstead metrics."""
        try:
            # Parse JSON to count structural elements
            data = json.loads(content)
            operators = []
            operands = []

            def traverse_json(obj, path=""):
                if isinstance(obj, dict):
                    operators.append('{')  # Object start
                    for key, value in obj.items():
                        operators.append(':')  # Key-value separator
                        operands.append(key)
                        traverse_json(value, f"{path}.{key}")
                    operators.append('}')  # Object end
                elif isinstance(obj, list):
                    operators.append('[')  # Array start
                    for i, item in enumerate(obj):
                        if i > 0:
                            operators.append(',')  # Array separator
                        traverse_json(item, f"{path}[{i}]")
                    operators.append(']')  # Array end
                else:
                    # Primitive values (strings, numbers, booleans, null)
                    operands.append(str(obj))

            traverse_json(data)

            unique_operators = len(set(operators))
            unique_operands = len(set(operands))
            total_operators = len(operators)
            total_operands = len(operands)

            return unique_operators, unique_operands, total_operators, total_operands

        except json.JSONDecodeError:
            return 0, 0, 0, 0

    def _remove_python_comments_and_strings(self, content: str) -> str:
        """Remove Python comments and string literals."""
        # Remove triple-quoted strings
        content = re.sub(r'""".*?"""', '', content, flags=re.DOTALL)
        content = re.sub(r"'''.*?'''", '', content, flags=re.DOTALL)

        # Remove single/double quoted strings
        content = re.sub(r'"[^"]*"', '', content)
        content = re.sub(r"'[^']*'", '', content)

        # Remove comments
        content = re.sub(r'#.*', '', content)

        return content

    def _remove_terraform_comments(self, content: str) -> str:
        """Remove Terraform comments."""
        # Remove single-line comments
        content = re.sub(r'#.*', '', content)
        content = re.sub(r'//.*', '', content)

        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

        return content

    def _is_python_operator(self, token: str) -> bool:
        """Check if token is a Python operator."""
        python_ops = {'+', '-', '*', '/', '%', '=', '<', '>', '!', '&', '|', '^', '~'}
        return any(op in token for op in python_ops)


def calculate_cyclomatic_complexity(content: str, extension: str) -> int:
    """
    Calculate a basic cyclomatic complexity estimate.
    In production, you'd use tools like radon for Python or custom parsers.
    """
    complexity = 1

    if extension == ".py":
        decision_keywords = ['if', 'elif', 'for', 'while', 'and', 'or', 'except', 'with']
        for keyword in decision_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', content))
    elif extension == ".tf":
        decision_keywords = ['count', 'for_each', 'if']
        for keyword in decision_keywords:
            complexity += len(re.findall(rf'\b{keyword}\b', content))

    return complexity


# ---------------------------
# Maintainability Index Functions
# ---------------------------
def halstead_volume(unique_operators, unique_operands, total_operators, total_operands):
    """Calculate Halstead Volume (HV)."""
    program_vocab = unique_operators + unique_operands
    program_length = total_operators + total_operands
    if program_vocab == 0 or program_length == 0:
        return 0
    return program_length * math.log2(program_vocab)


def maintainability_index(HV, CC, LOC, comment_lines, total_lines):
    """Calculate both original and Microsoft Maintainability Index."""
    if LOC == 0:
        return 0, 0
    if HV <= 0:
        HV = 1

    # Percentage of comments
    perCOM = (comment_lines / total_lines) if total_lines > 0 else 0
    perCOM = max(0.0, min(1.0, perCOM))

    # Maintability index formula
    base = 171 - 5.2 * math.log(HV) - 0.23 * CC - 16.2 * math.log(LOC)

    try:
        MI_original = base + 50 * math.sin(math.sqrt(2.4 * perCOM))
    except (ValueError, ZeroDivisionError):
        MI_original = 0

    try:
        MI_ms = max(0.0, min(100.0, (base * 100) / 171))
    except (ValueError, ZeroDivisionError, OverflowError):
        MI_ms = 0

    return MI_original, MI_ms


# ---------------------------
# LOC Counting Functions
# ---------------------------

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

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            lines = content.split('\n')

            for line in lines:
                total_lines += 1
                if not line.strip():
                    blank_lines += 1
                elif is_comment_line(line, extension):
                    comment_lines += 1

        sloc = total_lines - (blank_lines + comment_lines)  # Source Lines of Code
        ploc = total_lines  # Physical Lines of Code

        # Calculate actual Halstead metrics
        analyzer = HalsteadAnalyzer(extension)
        unique_operators, unique_operands, total_operators, total_operands = analyzer.analyze_content(content)

        HV = halstead_volume(unique_operators, unique_operands, total_operators, total_operands)
        CC = calculate_cyclomatic_complexity(content, extension)

        MI_orig, MI_ms = maintainability_index(HV, CC, sloc, comment_lines, total_lines)

        return {
            "file": filepath,
            "total": total_lines,
            "blank": blank_lines,
            "comments": comment_lines,
            "SLOC": sloc,
            "PLOC": ploc,
            "unique_operators": unique_operators,
            "unique_operands": unique_operands,
            "total_operators": total_operators,
            "total_operands": total_operands,
            "HV": HV,
            "CC": CC,
            "MI_original": MI_orig,
            "MI_ms": MI_ms
        }
    except Exception as e:
        print(f"Error processing file {filepath}: {e}")
        return None


def count_lines_in_directory(directory: str, excluded_folders: List[str] = None):
    """Walk through a directory and count LOC for all supported files."""
    if excluded_folders is None:
        excluded_folders = []

    results = []
    total_summary = {
        "total": 0, "blank": 0, "comments": 0, "SLOC": 0, "PLOC": 0,
        "unique_operators": 0, "unique_operands": 0, "total_operators": 0,
        "total_operands": 0, "HV": 0, "CC": 0, "MI_original": 0, "MI_ms": 0
    }

    for root, dirs, files in os.walk(directory):
        # Modify 'dirs' in-place to skip excluded folders
        dirs[:] = [d for d in dirs if d not in excluded_folders]

        for file in files:
            filepath = os.path.join(root, file)
            result = count_lines_in_file(filepath)
            if result:
                results.append(result)
                # Sum up metrics
                for key in ["total", "blank", "comments", "SLOC", "PLOC", "unique_operators",
                            "unique_operands", "total_operators", "total_operands", "CC"]:
                    total_summary[key] += result[key]

    # Calculate aggregate Halstead Volume and Maintainability Index
    if total_summary["unique_operators"] > 0 and total_summary["unique_operands"] > 0:
        total_summary["HV"] = halstead_volume(
            total_summary["unique_operators"],
            total_summary["unique_operands"],
            total_summary["total_operators"],
            total_summary["total_operands"]
        )

        total_summary["MI_original"], total_summary["MI_ms"] = maintainability_index(
            total_summary["HV"],
            total_summary["CC"],
            total_summary["SLOC"],
            total_summary["comments"],
            total_summary["total"]
        )

    return results, total_summary


if __name__ == "__main__":
    # folder_path = stack name: terraform/json_infra/pulumi
    folder_path = "cdk_stack_infrastructure"
    excluded_folders = [".venv", "__pycache__", ".git", "node_modules", ".terraform", "dependencies", "sql_schema", "naming_utils.py"]
    output_file = f"Halstead_{folder_path}.txt"

    results, summary = count_lines_in_directory(folder_path, excluded_folders)

    lines_out = []
    print("=" * 80)
    print("CODE METRICS ANALYSIS REPORT")
    print("=" * 80)

    for r in results:
        lines_out.append(
            f"{r['file']}: "
            f"\nSLOC={r['SLOC']}, \nPLOC={r['PLOC']}, "
            f"\nComments={r['comments']}, \nBlank={r['blank']}, "
            f"\nHV={r['HV']:.2f}, \nCC={r['CC']}, \nMI(orig)={r['MI_original']:.2f}, \nMI(ms)={r['MI_ms']:.2f}"
        )
        print(f"{r['file']}:")
        print(f"  Lines: SLOC={r['SLOC']}, PLOC={r['PLOC']}, Comments={r['comments']}, Blank={r['blank']}")
        print(
            f"  Halstead: Operators={r['unique_operators']}/{r['total_operators']}, Operands={r['unique_operands']}/{r['total_operands']}")
        print(f"  Metrics: HV={r['HV']:.2f}, CC={r['CC']}, MI(orig)={r['MI_original']:.2f}, MI(ms)={r['MI_ms']:.2f}")
        print()

    lines_out.append("\n" + "=" * 50)
    lines_out.append("SUMMARY")
    lines_out.append("=" * 50)
    lines_out.append(f"Total Physical Lines of Code (PLOC): {summary['PLOC']}")
    lines_out.append(f"Total Source Lines of Code (SLOC): {summary['SLOC']}")
    lines_out.append(f"Total Comments: {summary['comments']}")
    lines_out.append(f"Total Blank Lines: {summary['blank']}")
    lines_out.append(f"Unique Operators: {summary['unique_operators']}")
    lines_out.append(f"Unique Operands: {summary['unique_operands']}")
    lines_out.append(f"Total Operators: {summary['total_operators']}")
    lines_out.append(f"Total Operands: {summary['total_operands']}")
    lines_out.append(f"Halstead Volume: {summary['HV']:.2f}")
    lines_out.append(f"Cyclomatic Complexity: {summary['CC']}")
    lines_out.append(f"Maintainability Index (Original): {summary['MI_original']:.2f}")
    lines_out.append(f"Maintainability Index (Microsoft 0–100 scale): {summary['MI_ms']:.2f}")

    output_text = "\n".join(lines_out)

    # Print summary to console
    print("=" * 50)
    print("SUMMARY")
    print("=" * 50)
    print(f"Total Physical Lines of Code (PLOC): {summary['PLOC']}")
    print(f"Total Source Lines of Code (SLOC): {summary['SLOC']}")
    print(f"Total Comments: {summary['comments']}")
    print(f"Total Blank Lines: {summary['blank']}")
    print(f"Unique Operators: {summary['unique_operators']}")
    print(f"Unique Operands: {summary['unique_operands']}")
    print(f"Total Operators: {summary['total_operators']}")
    print(f"Total Operands: {summary['total_operands']}")
    print(f"Halstead Volume: {summary['HV']:.2f}")
    print(f"Cyclomatic Complexity: {summary['CC']}")
    print(f"Maintainability Index (Original): {summary['MI_original']:.2f}")
    print(f"Maintainability Index (Microsoft 0–100 scale): {summary['MI_ms']:.2f}")

    # Save to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"\nResults saved to {output_file}")