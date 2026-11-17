"""
CodeSentinel - Repository Service
Handles cloning GitHub repositories and extracting ZIP uploads.
"""

import os
import shutil
import tempfile
import zipfile
import logging
import re
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class RepoService:
    """Service for cloning and managing repository files."""

    def __init__(self):
        self.repos_dir = settings.repos_path

    async def clone_repo(self, repo_url: str, scan_id: str) -> str:
        """
        Clone a GitHub repository to a local directory.

        Args:
            repo_url: GitHub repository URL
            scan_id: Unique scan ID for directory naming

        Returns:
            Path to the cloned repository

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If cloning fails
        """
        # Validate and normalize the URL
        repo_url = self._normalize_github_url(repo_url)
        if not repo_url:
            raise ValueError("Invalid GitHub repository URL")

        dest_path = self.repos_dir / scan_id
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            import git
            logger.info(f"Cloning {repo_url} to {dest_path}")
            git.Repo.clone_from(
                repo_url,
                str(dest_path),
                depth=1,  # Shallow clone for speed
                single_branch=True,
            )
            logger.info(f"Successfully cloned {repo_url}")
            return str(dest_path)

        except Exception as e:
            # Clean up failed clone
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
            logger.error(f"Failed to clone {repo_url}: {e}")
            raise RuntimeError(f"Failed to clone repository: {e}")

    async def extract_zip(self, zip_path: str, scan_id: str) -> str:
        """
        Extract a ZIP file to a local directory.

        Args:
            zip_path: Path to the uploaded ZIP file
            scan_id: Unique scan ID for directory naming

        Returns:
            Path to the extracted repository
        """
        dest_path = self.repos_dir / scan_id
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Security: check for path traversal
                for name in zf.namelist():
                    if name.startswith("/") or ".." in name:
                        raise ValueError(f"Unsafe file path in ZIP: {name}")

                zf.extractall(str(dest_path))

            # If the ZIP contains a single root directory, use that
            contents = list(dest_path.iterdir())
            if len(contents) == 1 and contents[0].is_dir():
                # Move contents up one level
                inner_dir = contents[0]
                for item in inner_dir.iterdir():
                    shutil.move(str(item), str(dest_path / item.name))
                inner_dir.rmdir()

            logger.info(f"Successfully extracted ZIP to {dest_path}")
            return str(dest_path)

        except zipfile.BadZipFile:
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
            raise ValueError("Invalid or corrupted ZIP file")
        except Exception as e:
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
            raise RuntimeError(f"Failed to extract ZIP: {e}")

    async def save_upload(self, file_content: bytes, filename: str, scan_id: str) -> str:
        """Save an uploaded file to a temporary location."""
        upload_dir = self.repos_dir / "uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        file_path = upload_dir / f"{scan_id}_{filename}"
        with open(file_path, "wb") as f:
            f.write(file_content)

        return str(file_path)

    async def cleanup(self, scan_id: str):
        """Remove cloned/extracted files for a scan."""
        repo_dir = self.repos_dir / scan_id
        if repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
            logger.info(f"Cleaned up repo files for scan {scan_id}")

    @staticmethod
    def _normalize_github_url(url: str) -> Optional[str]:
        """Normalize and validate a GitHub repository URL."""
        url = url.strip().rstrip("/")

        # Remove .git suffix if present
        if url.endswith(".git"):
            url = url[:-4]

        # Pattern: https://github.com/user/repo
        github_pattern = re.compile(
            r'^https?://github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$'
        )

        match = github_pattern.match(url)
        if match:
            return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

        # Pattern: github.com/user/repo (missing protocol)
        short_pattern = re.compile(
            r'^github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$'
        )
        match = short_pattern.match(url)
        if match:
            return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

        return None

    @staticmethod
    def extract_repo_name(repo_url: str) -> str:
        """Extract the repository name from a URL."""
        url = repo_url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parts = url.split("/")
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return parts[-1] if parts else "unknown"


# Singleton
repo_service = RepoService()
