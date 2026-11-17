"""
CodeSentinel - Base Agent
Abstract base class for all analysis agents.
"""

from abc import ABC, abstractmethod
from typing import List
import logging


class BaseAgent(ABC):
    """Base class for all CodeSentinel analysis agents."""

    def __init__(self, name: str, agent_type: str):
        self.name = name
        self.agent_type = agent_type
        self.logger = logging.getLogger(f"agent.{name}")

    @abstractmethod
    async def analyze(self, files: List[dict], project_info: dict) -> List[dict]:
        """
        Analyze the given files and return a list of detected issues.

        Args:
            files: List of file dicts with keys: path, content, extension, lines
            project_info: Project metadata (languages, frameworks, etc.)

        Returns:
            List of issue dicts with keys:
                agent_type, severity, category, title, description,
                file_path, line_start, line_end, code_snippet,
                explanation, suggestion, suggested_code, original_code
        """
        pass

    def _create_issue(
        self,
        severity: str,
        category: str,
        title: str,
        description: str,
        file_path: str = None,
        line_start: int = None,
        line_end: int = None,
        code_snippet: str = None,
        explanation: str = None,
        suggestion: str = None,
        suggested_code: str = None,
        original_code: str = None,
    ) -> dict:
        """Helper to create a consistently formatted issue dict."""
        return {
            "agent_type": self.agent_type,
            "severity": severity,
            "category": category,
            "title": title,
            "description": description,
            "file_path": file_path,
            "line_start": line_start,
            "line_end": line_end,
            "code_snippet": code_snippet,
            "explanation": explanation,
            "suggestion": suggestion,
            "suggested_code": suggested_code,
            "original_code": original_code,
        }
