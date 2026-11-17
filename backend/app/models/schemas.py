"""
CodeSentinel - Pydantic Schemas
Request/Response models for the API layer.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime


# ── Request Schemas ──────────────────────────────────────────

class ScanRequest(BaseModel):
    """Request to start a new scan from a GitHub URL."""
    repo_url: str = Field(
        ...,
        description="GitHub repository URL to scan",
        examples=["https://github.com/user/repo"],
    )


class ScanUploadRequest(BaseModel):
    """Metadata for a ZIP upload scan (file sent as multipart)."""
    project_name: Optional[str] = Field(
        None,
        description="Optional project name override",
    )


# ── Response Schemas ─────────────────────────────────────────

class IssueResponse(BaseModel):
    """A single detected issue."""
    id: str
    agent_type: str
    severity: str
    category: str
    title: str
    description: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None
    explanation: Optional[str] = None
    suggestion: Optional[str] = None
    suggested_code: Optional[str] = None
    original_code: Optional[str] = None


class ScanSummary(BaseModel):
    """High-level scan metadata."""
    id: str
    repo_url: Optional[str] = None
    repo_name: str
    source_type: str
    status: str
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    languages: Optional[dict] = None
    frameworks: Optional[list] = None
    total_files: int = 0
    total_lines: int = 0
    total_issues: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    health_score: float = 100.0
    progress: float = 0.0
    current_step: str = "Initializing"
    error_message: Optional[str] = None


class ScanResponse(BaseModel):
    """Full scan response with issues."""
    scan: ScanSummary
    issues: List[IssueResponse] = []


class ScanCreatedResponse(BaseModel):
    """Response after creating a new scan."""
    scan_id: str
    status: str
    message: str


class HealthResponse(BaseModel):
    """API health check response."""
    status: str = "healthy"
    app_name: str
    version: str
    llm_available: bool


class ScanListResponse(BaseModel):
    """List of scans."""
    scans: List[ScanSummary]
    total: int


# ── WebSocket Schemas ────────────────────────────────────────

class ProgressUpdate(BaseModel):
    """Real-time progress update sent via WebSocket."""
    scan_id: str
    status: str
    progress: float
    current_step: str
    issues_found: int = 0
    message: Optional[str] = None
