"""
CodeSentinel - File Utilities
Helper functions for reading, filtering, and processing source code files.
"""

import os
from pathlib import Path
from typing import List, Optional

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False

from app.config import settings


def get_source_files(repo_path: str) -> List[dict]:
    """
    Walk the repository and collect all source code files for analysis.
    Returns a list of file info dicts with path, extension, size, and content.
    """
    files = []
    repo = Path(repo_path)
    file_count = 0

    for root, dirs, filenames in os.walk(repo):
        # Skip ignored directories (modify dirs in-place to prevent os.walk from descending)
        dirs[:] = [
            d for d in dirs
            if d not in settings.SKIP_DIRECTORIES and not d.startswith(".")
        ]

        for filename in filenames:
            if file_count >= settings.MAX_TOTAL_FILES:
                break

            filepath = Path(root) / filename
            ext = filepath.suffix.lower()

            # Only process supported file types
            if ext not in settings.SUPPORTED_EXTENSIONS:
                continue

            # Skip files that are too large
            try:
                size_kb = filepath.stat().st_size / 1024
                if size_kb > settings.MAX_FILE_SIZE_KB:
                    continue
            except OSError:
                continue

            # Read file content
            content = read_file_safe(str(filepath))
            if content is None:
                continue

            relative_path = str(filepath.relative_to(repo))
            line_count = content.count("\n") + 1

            files.append({
                "path": relative_path,
                "absolute_path": str(filepath),
                "extension": ext,
                "size_kb": round(size_kb, 2),
                "lines": line_count,
                "content": content,
            })
            file_count += 1

    return files


def read_file_safe(filepath: str) -> Optional[str]:
    """Read a file with automatic encoding detection. Returns None if unreadable."""
    try:
        # Try UTF-8 first (most common)
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        pass

    # Fall back to chardet if available
    if CHARDET_AVAILABLE:
        try:
            with open(filepath, "rb") as f:
                raw = f.read()
            detected = chardet.detect(raw)
            encoding = detected.get("encoding", "utf-8")
            return raw.decode(encoding, errors="replace")
        except Exception:
            pass

    # Generic fallback: read with UTF-8 replacing invalid bytes
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return None


def get_file_lines(content: str, start: int, end: int, context: int = 3) -> str:
    """Extract specific lines from file content with surrounding context."""
    lines = content.split("\n")
    ctx_start = max(0, start - context - 1)
    ctx_end = min(len(lines), end + context)
    return "\n".join(lines[ctx_start:ctx_end])


def find_dependency_files(repo_path: str) -> List[dict]:
    """Find all dependency/package manager files in the repository."""
    dep_files = []
    repo = Path(repo_path)

    for dep_file_name in settings.DEPENDENCY_FILES:
        # Check root directory
        root_file = repo / dep_file_name
        if root_file.exists():
            content = read_file_safe(str(root_file))
            if content:
                dep_files.append({
                    "name": dep_file_name,
                    "path": dep_file_name,
                    "absolute_path": str(root_file),
                    "content": content,
                    "type": _classify_dep_file(dep_file_name),
                })

        # Check one level deep (monorepo support)
        for subdir in repo.iterdir():
            if subdir.is_dir() and subdir.name not in settings.SKIP_DIRECTORIES:
                sub_file = subdir / dep_file_name
                if sub_file.exists():
                    content = read_file_safe(str(sub_file))
                    if content:
                        dep_files.append({
                            "name": dep_file_name,
                            "path": str(sub_file.relative_to(repo)),
                            "absolute_path": str(sub_file),
                            "content": content,
                            "type": _classify_dep_file(dep_file_name),
                        })

    return dep_files


def _classify_dep_file(filename: str) -> str:
    """Classify the dependency file type by its filename."""
    mapping = {
        "requirements.txt": "python-pip",
        "Pipfile": "python-pipenv",
        "pyproject.toml": "python-pyproject",
        "setup.py": "python-setup",
        "package.json": "node-npm",
        "yarn.lock": "node-yarn",
        "pnpm-lock.yaml": "node-pnpm",
        "pom.xml": "java-maven",
        "build.gradle": "java-gradle",
        "build.gradle.kts": "java-gradle",
        "Gemfile": "ruby-bundler",
        "composer.json": "php-composer",
        "go.mod": "go-mod",
        "Cargo.toml": "rust-cargo",
    }
    return mapping.get(filename, "unknown")
