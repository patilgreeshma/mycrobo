"""
CodeSentinel - Application Configuration
Loads settings from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from .env file and environment variables."""

    # Application
    APP_NAME: str = "CodeSentinel"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./codesentinel.db"

    # Google Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Repository Settings
    REPOS_DIR: str = "./repos"
    MAX_FILE_SIZE_KB: int = 500
    MAX_TOTAL_FILES: int = 1000

    # Supported file extensions for analysis
    SUPPORTED_EXTENSIONS: List[str] = [
        ".py", ".js", ".ts", ".jsx", ".tsx",
        ".java", ".kt", ".scala",
        ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".swift",
        ".rb", ".php",
        ".html", ".css", ".scss",
        ".sql",
        ".yaml", ".yml", ".json", ".toml", ".xml",
        ".sh", ".bash",
        ".dockerfile", ".tf",
    ]

    # Files to skip during analysis
    SKIP_DIRECTORIES: List[str] = [
        "node_modules", ".git", "__pycache__", ".venv", "venv",
        "env", ".env", "dist", "build", ".next", ".nuxt",
        "vendor", "target", "bin", "obj", ".idea", ".vscode",
        "coverage", ".pytest_cache", ".mypy_cache",
    ]

    # Dependency files to look for
    DEPENDENCY_FILES: List[str] = [
        "requirements.txt", "Pipfile", "pyproject.toml", "setup.py",
        "package.json", "yarn.lock", "pnpm-lock.yaml",
        "pom.xml", "build.gradle", "build.gradle.kts",
        "Gemfile", "composer.json",
        "go.mod", "Cargo.toml",
    ]

    @property
    def repos_path(self) -> Path:
        """Get the absolute path for cloned repositories."""
        path = Path(self.REPOS_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def has_gemini_key(self) -> bool:
        """Check if a valid Gemini API key is configured."""
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_gemini_api_key_here")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
