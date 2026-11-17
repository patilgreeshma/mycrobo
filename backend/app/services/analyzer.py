"""
CodeSentinel - Project Analyzer
Analyzes repository structure, identifies languages, frameworks,
and prepares files for the analysis agents.
"""

import logging
from typing import Dict, List, Any

from app.utils.file_utils import get_source_files, find_dependency_files
from app.utils.language_detector import detect_languages, detect_frameworks

logger = logging.getLogger(__name__)


class ProjectAnalyzer:
    """Analyzes a repository's structure and metadata."""

    async def analyze(self, repo_path: str) -> Dict[str, Any]:
        """
        Perform full project analysis.

        Args:
            repo_path: Path to the repository root

        Returns:
            Dictionary with project metadata, files, and dependency info
        """
        logger.info(f"Analyzing project at {repo_path}")

        # Collect source files
        files = get_source_files(repo_path)
        logger.info(f"Found {len(files)} source files")

        # Detect languages
        languages = detect_languages(files)
        primary_language = list(languages.keys())[0] if languages else "unknown"
        logger.info(f"Detected languages: {languages}")

        # Find dependency files
        dep_files = find_dependency_files(repo_path)
        logger.info(f"Found {len(dep_files)} dependency files")

        # Detect frameworks
        frameworks = detect_frameworks(files, dep_files)
        logger.info(f"Detected frameworks: {frameworks}")

        # Calculate totals
        total_lines = sum(f["lines"] for f in files)

        # Build project info
        project_info = {
            "repo_path": repo_path,
            "languages": languages,
            "primary_language": primary_language,
            "frameworks": frameworks,
            "total_files": len(files),
            "total_lines": total_lines,
            "dependency_files": dep_files,
            "file_extensions": self._count_extensions(files),
            "structure": self._analyze_structure(files),
        }

        return {
            "project_info": project_info,
            "files": files,
        }

    def _count_extensions(self, files: List[dict]) -> Dict[str, int]:
        """Count files by extension."""
        ext_counts = {}
        for f in files:
            ext = f["extension"]
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        return dict(sorted(ext_counts.items(), key=lambda x: x[1], reverse=True))

    def _analyze_structure(self, files: List[dict]) -> Dict[str, Any]:
        """Analyze the project directory structure."""
        directories = set()
        for f in files:
            parts = f["path"].split("/")
            for i in range(1, len(parts)):
                directories.add("/".join(parts[:i]))

        # Identify common patterns
        has_tests = any(
            "test" in d.lower() or "spec" in d.lower()
            for d in directories
        )
        has_docs = any("doc" in d.lower() for d in directories)
        has_ci = any(
            d in (".github/workflows", ".gitlab-ci", ".circleci", "jenkins")
            for d in directories
        )
        has_docker = any(
            f["path"].lower() in ("dockerfile", "docker-compose.yml", "docker-compose.yaml")
            for f in files
        )

        return {
            "total_directories": len(directories),
            "has_tests": has_tests,
            "has_docs": has_docs,
            "has_ci": has_ci,
            "has_docker": has_docker,
        }


# Singleton
project_analyzer = ProjectAnalyzer()
