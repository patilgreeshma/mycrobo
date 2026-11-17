"""
CodeSentinel - Repository Service
Handles cloning GitHub repositories and extracting ZIP uploads.
Uses system git CLI by default, with GitPython fallback.
"""

import os
import shutil
import tempfile
import zipfile
import logging
import re
import asyncio
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
        Clone a Git repository to a local directory.

        Args:
            repo_url: Repository URL or shorthand (e.g., owner/repo)
            scan_id: Unique scan ID for directory naming

        Returns:
            Path to the cloned repository

        Raises:
            ValueError: If the URL is invalid
            RuntimeError: If cloning fails
        """
        normalized_url = self._normalize_github_url(repo_url)
        if not normalized_url:
            raise ValueError(f"Invalid repository URL or shorthand: '{repo_url}'")

        dest_path = self.repos_dir / scan_id
        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)
        dest_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"Cloning {normalized_url} to {dest_path}")

        # 1. Try system git CLI first (fast, shallow clone, async)
        git_bin = shutil.which("git")
        err_msg = ""
        if git_bin:
            try:
                cmd = [
                    git_bin,
                    "clone",
                    "--depth", "1",
                    "--single-branch",
                    normalized_url,
                    str(dest_path),
                ]
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    stdout, stderr = await asyncio.wait_for(
                        proc.communicate(), timeout=120
                    )
                except asyncio.TimeoutError:
                    proc.kill()
                    raise RuntimeError(
                        "Repository clone timed out after 120 seconds. "
                        "The repository may be too large or the network is slow."
                    )
                if proc.returncode == 0:
                    logger.info(f"Successfully cloned {normalized_url} using git CLI")
                    return str(dest_path)
                else:
                    err_msg = stderr.decode(errors="replace").strip()
                    logger.warning(f"git clone failed (code {proc.returncode}): {err_msg}")
            except Exception as e:
                err_msg = str(e)
                logger.warning(f"git subprocess failed: {e}")

        # 2. Try GitPython fallback if installed
        try:
            import git
            git.Repo.clone_from(
                normalized_url,
                str(dest_path),
                depth=1,
                single_branch=True,
            )
            logger.info(f"Successfully cloned {normalized_url} using GitPython")
            return str(dest_path)
        except ImportError:
            pass
        except Exception as e:
            err_msg = str(e)

        # If we reached here, cloning failed
        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)

        detail = err_msg or "git command failed or repository not accessible"
        logger.error(f"Failed to clone {repo_url}: {detail}")
        raise RuntimeError(f"Failed to clone repository: {detail}")

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
        if dest_path.exists():
            shutil.rmtree(dest_path, ignore_errors=True)
        dest_path.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Security: prevent zip-slip (path traversal)
                for member in zf.infolist():
                    target_path = dest_path / member.filename
                    resolved = target_path.resolve()
                    if not str(resolved).startswith(str(dest_path.resolve())):
                        raise ValueError(f"Zip-slip vulnerability detected: {member.filename}")

                zf.extractall(dest_path)

            # If the ZIP contained a single top-level directory, descend into it
            entries = [e for e in dest_path.iterdir() if not e.name.startswith(".")]
            if len(entries) == 1 and entries[0].is_dir():
                # Move contents up one level
                temp_dir = dest_path.parent / f"{scan_id}_temp"
                entries[0].rename(temp_dir)
                dest_path.rmdir()
                temp_dir.rename(dest_path)

            logger.info(f"Successfully extracted {zip_path} to {dest_path}")
            return str(dest_path)

        except Exception as e:
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
            logger.error(f"Failed to extract {zip_path}: {e}")
            raise RuntimeError(f"Failed to extract ZIP: {e}")

    async def save_upload(self, file_content: bytes, filename: str, scan_id: str) -> str:
        """Save uploaded file bytes to a temporary location."""
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
        """
        Normalize and validate a Git repository URL or shorthand.
        Accepts:
          - owner/repo (e.g. nomercy77/antislop)
          - github.com/owner/repo
          - https://github.com/owner/repo
          - https://github.com/owner/repo.git
          - git@github.com:owner/repo.git
          - https://gitlab.com/...
        """
        if not url:
            return None

        url = url.strip().rstrip("/")

        # SSH pattern: git@...
        if url.startswith("git@"):
            return url

        # Direct owner/repo shorthand: e.g. "nomercy77/antislop"
        short_owner_repo = re.compile(r'^([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)$')
        match = short_owner_repo.match(url)
        if match:
            return f"https://github.com/{match.group(1)}/{match.group(2)}.git"

        # Remove .git suffix if present for clean matching
        clean_url = url[:-4] if url.endswith(".git") else url

        # Full HTTPS / HTTP URL
        if clean_url.startswith("http://") or clean_url.startswith("https://"):
            return f"{clean_url}.git"

        # Missing protocol with domain: e.g. github.com/owner/repo or gitlab.com/owner/repo
        if "/" in clean_url and "." in clean_url.split("/")[0]:
            return f"https://{clean_url}.git"

        return None

    @staticmethod
    def extract_repo_name(repo_url: str) -> str:
        """Extract the user/repo name from a URL or shorthand."""
        url = repo_url.strip().rstrip("/")
        if url.endswith(".git"):
            url = url[:-4]
        parts = [p for p in url.split("/") if p and p not in ("https:", "http:", "github.com", "gitlab.com")]
        if len(parts) >= 2:
            return f"{parts[-2]}/{parts[-1]}"
        return parts[-1] if parts else "codebase"


# Singleton
repo_service = RepoService()
