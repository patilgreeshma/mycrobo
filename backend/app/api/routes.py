"""
CodeSentinel - API Routes
REST endpoints for scan management and report retrieval.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.config import settings
from app.models.database import get_db
from app.models.orm_models import Scan, Issue, SEVERITY_ORDER
from app.models.schemas import (
    ScanRequest,
    ScanCreatedResponse,
    ScanSummary,
    ScanResponse,
    IssueResponse,
    HealthResponse,
    ScanListResponse,
)
from app.services.repo_service import repo_service
from app.services.analyzer import project_analyzer
from app.services.report_generator import report_generator
from app.agents.orchestrator import run_audit
from app.api.websocket import progress_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["scans"])


# ── Health Check ─────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health check endpoint."""
    from app.utils.llm_client import llm_client
    return HealthResponse(
        status="healthy",
        app_name=settings.APP_NAME,
        version=settings.APP_VERSION,
        llm_available=llm_client.available,
    )


# ── Create Scan ──────────────────────────────────────────────

@router.post("/scans", response_model=ScanCreatedResponse)
async def create_scan(request: ScanRequest, db: AsyncSession = Depends(get_db)):
    """Start a new codebase audit scan from a GitHub URL."""
    # Create scan record
    scan_id = str(uuid.uuid4())
    repo_name = repo_service.extract_repo_name(request.repo_url)

    scan = Scan(
        id=scan_id,
        repo_url=request.repo_url,
        repo_name=repo_name,
        source_type="github",
        status="pending",
    )
    db.add(scan)
    await db.commit()

    # Start the scan in background
    asyncio.create_task(_run_scan(scan_id, request.repo_url, db_url=settings.DATABASE_URL))

    return ScanCreatedResponse(
        scan_id=scan_id,
        status="pending",
        message=f"Scan initiated for {repo_name}. Connect to WebSocket /ws/scan/{scan_id} for live updates.",
    )


@router.post("/scans/upload", response_model=ScanCreatedResponse)
async def create_scan_from_upload(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Start a new scan from an uploaded ZIP file."""
    if not file.filename.endswith(".zip"):
        raise HTTPException(400, "Only ZIP files are supported")

    scan_id = str(uuid.uuid4())
    name = project_name or file.filename.replace(".zip", "")

    # Save the uploaded file
    content = await file.read()
    zip_path = await repo_service.save_upload(content, file.filename, scan_id)

    scan = Scan(
        id=scan_id,
        repo_name=name,
        source_type="zip",
        status="pending",
    )
    db.add(scan)
    await db.commit()

    # Start scan in background
    asyncio.create_task(
        _run_scan(scan_id, zip_path=zip_path, db_url=settings.DATABASE_URL)
    )

    return ScanCreatedResponse(
        scan_id=scan_id,
        status="pending",
        message=f"Scan initiated for {name}.",
    )


# ── Get Scan Status / Results ────────────────────────────────

@router.get("/scans", response_model=ScanListResponse)
async def list_scans(
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List all scans, most recent first."""
    result = await db.execute(
        select(Scan).order_by(desc(Scan.created_at)).offset(offset).limit(limit)
    )
    scans = result.scalars().all()

    total_result = await db.execute(select(Scan))
    total = len(total_result.scalars().all())

    return ScanListResponse(
        scans=[ScanSummary(**s.to_dict()) for s in scans],
        total=total,
    )


@router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Get scan details and all issues."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(404, "Scan not found")

    # Get issues
    issues_result = await db.execute(
        select(Issue).where(Issue.scan_id == scan_id).order_by(Issue.severity_order)
    )
    issues = issues_result.scalars().all()

    return {
        "scan": scan.to_dict(),
        "issues": [issue.to_dict() for issue in issues],
    }


@router.get("/scans/{scan_id}/progress")
async def get_scan_progress(scan_id: str):
    """Get current scan progress (polling fallback for WebSocket)."""
    return progress_manager.get_latest(scan_id)


@router.get("/scans/{scan_id}/report")
async def get_report(scan_id: str, format: str = "json", db: AsyncSession = Depends(get_db)):
    """Get the audit report in JSON or Markdown format."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(404, "Scan not found")

    if scan.status != "complete":
        raise HTTPException(400, f"Scan is not complete. Current status: {scan.status}")

    issues_result = await db.execute(
        select(Issue).where(Issue.scan_id == scan_id).order_by(Issue.severity_order)
    )
    issues = issues_result.scalars().all()

    if format == "markdown":
        markdown = report_generator.generate_markdown(scan, issues)
        return {"format": "markdown", "content": markdown}
    else:
        return report_generator.generate_json(scan, issues)


@router.delete("/scans/{scan_id}")
async def delete_scan(scan_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a scan and its associated data."""
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()

    if not scan:
        raise HTTPException(404, "Scan not found")

    await db.delete(scan)
    await db.commit()

    # Clean up repo files
    await repo_service.cleanup(scan_id)

    return {"message": "Scan deleted successfully"}


# ── WebSocket Endpoint ───────────────────────────────────────

@router.websocket("/ws/scan/{scan_id}")
async def websocket_scan_progress(websocket: WebSocket, scan_id: str):
    """WebSocket endpoint for real-time scan progress updates."""
    await progress_manager.connect(scan_id, websocket)
    try:
        while True:
            # Keep connection alive; wait for disconnect
            await websocket.receive_text()
    except WebSocketDisconnect:
        await progress_manager.disconnect(scan_id, websocket)


# ── Background Scan Runner ──────────────────────────────────

async def _run_scan(
    scan_id: str,
    repo_url: str = None,
    zip_path: str = None,
    db_url: str = None,
):
    """
    Background task that executes the full scan pipeline.
    Uses its own database session since it runs outside the request lifecycle.
    """
    from app.models.database import async_session_factory

    async with async_session_factory() as db:
        try:
            # Fetch the scan
            result = await db.execute(select(Scan).where(Scan.id == scan_id))
            scan = result.scalar_one()

            # === Step 1: Clone/Extract ===
            scan.status = "cloning"
            scan.progress = 0.05
            scan.current_step = "Cloning repository..." if repo_url else "Extracting files..."
            await db.commit()
            await _update_progress(scan_id, scan)

            if repo_url:
                repo_path = await repo_service.clone_repo(repo_url, scan_id)
            elif zip_path:
                repo_path = await repo_service.extract_zip(zip_path, scan_id)
            else:
                raise ValueError("No repository URL or ZIP path provided")

            scan.repo_path = repo_path

            # === Step 2: Analyze Project ===
            scan.status = "analyzing"
            scan.progress = 0.10
            scan.current_step = "Analyzing project structure..."
            await db.commit()
            await _update_progress(scan_id, scan)

            analysis = await project_analyzer.analyze(repo_path)
            project_info = analysis["project_info"]
            files = analysis["files"]

            scan.languages = project_info["languages"]
            scan.frameworks = project_info["frameworks"]
            scan.total_files = project_info["total_files"]
            scan.total_lines = project_info["total_lines"]
            await db.commit()

            # === Step 3: Run Agent Pipeline ===
            scan.status = "scanning"
            scan.progress = 0.15
            scan.current_step = "Running analysis agents..."
            await db.commit()
            await _update_progress(scan_id, scan)

            async def on_progress(progress: float, step: str):
                scan.progress = progress
                scan.current_step = step
                await db.commit()
                await _update_progress(scan_id, scan)

            audit_result = await run_audit(
                scan_id=scan_id,
                repo_path=repo_path,
                project_info=project_info,
                files=files,
                progress_callback=on_progress,
            )

            # === Step 4: Save Issues ===
            all_issues = audit_result.get("all_issues", [])
            report_data = audit_result.get("report", {})

            for issue_data in all_issues:
                issue = Issue(
                    scan_id=scan_id,
                    agent_type=issue_data.get("agent_type", "unknown"),
                    severity=issue_data.get("severity", "info"),
                    category=issue_data.get("category", "general"),
                    title=issue_data.get("title", "Untitled Issue"),
                    description=issue_data.get("description", ""),
                    file_path=issue_data.get("file_path"),
                    line_start=issue_data.get("line_start"),
                    line_end=issue_data.get("line_end"),
                    code_snippet=issue_data.get("code_snippet"),
                    explanation=issue_data.get("explanation"),
                    suggestion=issue_data.get("suggestion"),
                    suggested_code=issue_data.get("suggested_code"),
                    original_code=issue_data.get("original_code"),
                )
                db.add(issue)

            # === Step 5: Finalize ===
            severity_counts = report_data.get("severity_counts", {})
            scan.total_issues = len(all_issues)
            scan.critical_count = severity_counts.get("critical", 0)
            scan.high_count = severity_counts.get("high", 0)
            scan.medium_count = severity_counts.get("medium", 0)
            scan.low_count = severity_counts.get("low", 0)
            scan.info_count = severity_counts.get("info", 0)
            scan.health_score = report_data.get("health_score", 100.0)
            scan.status = "complete"
            scan.progress = 1.0
            scan.current_step = "Scan complete"
            scan.completed_at = datetime.now(timezone.utc)

            await db.commit()
            await _update_progress(scan_id, scan)

            logger.info(
                f"Scan {scan_id} complete: {len(all_issues)} issues found, "
                f"health score: {scan.health_score:.0f}/100"
            )

        except Exception as e:
            logger.error(f"Scan {scan_id} failed: {e}", exc_info=True)
            try:
                scan.status = "failed"
                scan.error_message = str(e)[:500]
                scan.progress = 0
                scan.current_step = f"Failed: {str(e)[:100]}"
                await db.commit()
                await _update_progress(scan_id, scan)
            except Exception:
                pass


async def _update_progress(scan_id: str, scan: Scan):
    """Send progress update via WebSocket."""
    await progress_manager.send_progress(scan_id, {
        "scan_id": scan_id,
        "status": scan.status,
        "progress": scan.progress,
        "current_step": scan.current_step,
        "total_issues": scan.total_issues or 0,
        "error_message": scan.error_message,
        "health_score": scan.health_score,
    })
