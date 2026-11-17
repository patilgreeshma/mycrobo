import os
import pytest
from app.services.analyzer import project_analyzer
from app.agents.orchestrator import run_audit
from app.services.report_generator import report_generator

@pytest.mark.asyncio
async def test_full_audit_pipeline_on_sample_repo():
    repo_path = os.path.abspath("tests/sample_repos/vulnerable_app")
    assert os.path.exists(repo_path)

    # 1. Structural Analysis
    analysis = await project_analyzer.analyze(repo_path)
    assert "project_info" in analysis
    assert "files" in analysis
    
    project_info = analysis["project_info"]
    files = analysis["files"]

    assert project_info["total_files"] >= 3
    assert "Python" in project_info["languages"]
    assert "Flask" in project_info["frameworks"]

    # 2. Agent Orchestration Pipeline
    progress_updates = []
    async def track_progress(prog, step):
        progress_updates.append((prog, step))

    audit_result = await run_audit(
        scan_id="test-scan-123",
        repo_path=repo_path,
        project_info=project_info,
        files=files,
        progress_callback=track_progress,
    )

    all_issues = audit_result.get("all_issues", [])
    assert len(all_issues) > 0
    assert len(progress_updates) > 0

    # Ensure issues from multiple agents are found
    agent_types = {issue["agent_type"] for issue in all_issues}
    assert "security" in agent_types
    assert "completeness" in agent_types
    assert "quality" in agent_types
    assert "dependency" in agent_types

    # 3. Report Generation
    report = audit_result.get("report", {})
    assert "health_score" in report
    assert report["health_score"] < 100.0  # Should be penalized for vulnerabilities
    assert report["severity_counts"]["critical"] > 0 or report["severity_counts"]["high"] > 0
