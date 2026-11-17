"""
CodeSentinel - SQLAlchemy ORM Models
Defines the database schema for scans, issues, and reports.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Scan(Base):
    """Represents a codebase audit scan."""

    __tablename__ = "scans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    repo_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="github")  # github | zip
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # Status flow: pending → cloning → analyzing → scanning → enhancing → complete | failed

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Project metadata
    languages: Mapped[Optional[dict]] = mapped_column(JSON, default=dict)
    frameworks: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    total_lines: Mapped[int] = mapped_column(Integer, default=0)
    repo_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Issue counts
    total_issues: Mapped[int] = mapped_column(Integer, default=0)
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)

    # Score (0-100, higher is better)
    health_score: Mapped[float] = mapped_column(Float, default=100.0)

    # Progress tracking
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    current_step: Mapped[str] = mapped_column(String(100), default="Initializing")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    issues: Mapped[List["Issue"]] = relationship(
        "Issue", back_populates="scan", cascade="all, delete-orphan",
        order_by="Issue.severity_order"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "repo_url": self.repo_url,
            "repo_name": self.repo_name,
            "source_type": self.source_type,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "languages": self.languages,
            "frameworks": self.frameworks,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "info_count": self.info_count,
            "health_score": self.health_score,
            "progress": self.progress,
            "current_step": self.current_step,
            "error_message": self.error_message,
        }


# Severity order mapping for sorting (lower = more severe)
SEVERITY_ORDER = {"critical": 1, "high": 2, "medium": 3, "low": 4, "info": 5}


class Issue(Base):
    """Represents a detected issue in the codebase."""

    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    scan_id: Mapped[str] = mapped_column(String(36), ForeignKey("scans.id"), nullable=False)

    # Classification
    agent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Agent types: security | quality | completeness | dependency
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    # Severities: critical | high | medium | low | info
    severity_order: Mapped[int] = mapped_column(Integer, default=5)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # e.g., hardcoded_secret, sql_injection, duplicate_code, missing_validation

    # Issue details
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # Location
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    code_snippet: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # LLM-enhanced fields
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggested_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    scan: Mapped["Scan"] = relationship("Scan", back_populates="issues")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if "severity" in kwargs and "severity_order" not in kwargs:
            self.severity_order = SEVERITY_ORDER.get(kwargs["severity"], 5)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "scan_id": self.scan_id,
            "agent_type": self.agent_type,
            "severity": self.severity,
            "severity_order": self.severity_order,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "code_snippet": self.code_snippet,
            "explanation": self.explanation,
            "suggestion": self.suggestion,
            "suggested_code": self.suggested_code,
            "original_code": self.original_code,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
