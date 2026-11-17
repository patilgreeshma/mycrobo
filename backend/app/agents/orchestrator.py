"""
CodeSentinel - Agent Orchestrator
Uses LangGraph to orchestrate the multi-agent analysis pipeline.
Coordinates Security, Quality, Completeness, and Dependency agents.
"""

import logging
from typing import TypedDict, List, Optional, Any
from datetime import datetime, timezone

from app.agents.security_agent import SecurityAgent
from app.agents.quality_agent import QualityAgent
from app.agents.completeness_agent import CompletenessAgent
from app.agents.dependency_agent import DependencyAgent
from app.utils.llm_client import llm_client

logger = logging.getLogger(__name__)


# Try to import LangGraph; fall back to simple sequential execution
try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.info("LangGraph not installed. Using simple sequential orchestrator.")


# ── State Definition ─────────────────────────────────────────

class AuditState(TypedDict):
    """State passed through the audit pipeline."""
    scan_id: str
    repo_path: str
    project_info: dict
    files: list
    security_issues: list
    quality_issues: list
    completeness_issues: list
    dependency_issues: list
    all_issues: list
    report: dict
    status: str
    progress: float
    current_step: str
    error: Optional[str]


# ── Agent Instances ──────────────────────────────────────────

security_agent = SecurityAgent()
quality_agent = QualityAgent()
completeness_agent = CompletenessAgent()
dependency_agent = DependencyAgent()


# ── LangGraph Node Functions ────────────────────────────────

async def security_scan_node(state: AuditState) -> dict:
    """Run the security analysis agent."""
    logger.info(f"[{state['scan_id']}] Running security scan...")
    try:
        issues = await security_agent.analyze(state["files"], state["project_info"])
        logger.info(f"[{state['scan_id']}] Security scan found {len(issues)} issues")
        return {
            "security_issues": issues,
            "progress": 0.35,
            "current_step": "Security scan complete",
        }
    except Exception as e:
        logger.error(f"Security scan error: {e}")
        return {"security_issues": [], "progress": 0.35, "current_step": "Security scan completed with errors"}


async def quality_scan_node(state: AuditState) -> dict:
    """Run the code quality agent."""
    logger.info(f"[{state['scan_id']}] Running quality scan...")
    try:
        issues = await quality_agent.analyze(state["files"], state["project_info"])
        logger.info(f"[{state['scan_id']}] Quality scan found {len(issues)} issues")
        return {
            "quality_issues": issues,
            "progress": 0.55,
            "current_step": "Quality analysis complete",
        }
    except Exception as e:
        logger.error(f"Quality scan error: {e}")
        return {"quality_issues": [], "progress": 0.55, "current_step": "Quality scan completed with errors"}


async def completeness_scan_node(state: AuditState) -> dict:
    """Run the completeness agent."""
    logger.info(f"[{state['scan_id']}] Running completeness scan...")
    try:
        issues = await completeness_agent.analyze(state["files"], state["project_info"])
        logger.info(f"[{state['scan_id']}] Completeness scan found {len(issues)} issues")
        return {
            "completeness_issues": issues,
            "progress": 0.70,
            "current_step": "Completeness analysis complete",
        }
    except Exception as e:
        logger.error(f"Completeness scan error: {e}")
        return {"completeness_issues": [], "progress": 0.70, "current_step": "Completeness scan completed with errors"}


async def dependency_scan_node(state: AuditState) -> dict:
    """Run the dependency analysis agent."""
    logger.info(f"[{state['scan_id']}] Running dependency scan...")
    try:
        issues = await dependency_agent.analyze(state["files"], state["project_info"])
        logger.info(f"[{state['scan_id']}] Dependency scan found {len(issues)} issues")
        return {
            "dependency_issues": issues,
            "progress": 0.80,
            "current_step": "Dependency analysis complete",
        }
    except Exception as e:
        logger.error(f"Dependency scan error: {e}")
        return {"dependency_issues": [], "progress": 0.80, "current_step": "Dependency scan completed with errors"}


async def merge_and_enhance_node(state: AuditState) -> dict:
    """Merge all agent results and enhance with LLM if available."""
    logger.info(f"[{state['scan_id']}] Merging results and enhancing with LLM...")

    all_issues = (
        state.get("security_issues", [])
        + state.get("quality_issues", [])
        + state.get("completeness_issues", [])
        + state.get("dependency_issues", [])
    )

    # Enhance issues without explanations using LLM
    if llm_client.available:
        # Group issues by file for batch enhancement
        issues_by_file = {}
        for issue in all_issues:
            fp = issue.get("file_path", "__global__")
            if fp not in issues_by_file:
                issues_by_file[fp] = []
            issues_by_file[fp].append(issue)

        # Enhance issues for up to top 5 files with detected issues
        for file_path, file_issues in list(issues_by_file.items())[:5]:
            # Only enhance issues missing explanations
            needs_enhancement = [i for i in file_issues if not i.get("explanation")]
            if needs_enhancement and file_path != "__global__":
                # Find the file content
                file_content = ""
                for f in state.get("files", []):
                    if f["path"] == file_path:
                        file_content = f["content"]
                        break

                if file_content:
                    language = state["project_info"].get("primary_language", "unknown")
                    try:
                        enhanced = await llm_client.analyze_code_issues(
                            file_content, file_path, needs_enhancement, language
                        )
                        # Update the issues in-place
                        for i, enhanced_issue in enumerate(enhanced):
                            if i < len(needs_enhancement):
                                needs_enhancement[i].update({
                                    k: v for k, v in enhanced_issue.items()
                                    if v and k in ("explanation", "suggestion", "suggested_code", "original_code")
                                })
                    except Exception as e:
                        logger.warning(f"LLM enhancement failed for {file_path}: {e}")

    return {
        "all_issues": all_issues,
        "progress": 0.90,
        "current_step": "Analysis complete, generating report",
    }


async def generate_report_node(state: AuditState) -> dict:
    """Generate the final audit report."""
    all_issues = state.get("all_issues", [])

    # Count by severity
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for issue in all_issues:
        sev = issue.get("severity", "info")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # Count by agent
    agent_counts = {"security": 0, "quality": 0, "completeness": 0, "dependency": 0}
    for issue in all_issues:
        agent = issue.get("agent_type", "unknown")
        agent_counts[agent] = agent_counts.get(agent, 0) + 1

    # Calculate health score (0-100)
    deductions = (
        severity_counts["critical"] * 15
        + severity_counts["high"] * 8
        + severity_counts["medium"] * 3
        + severity_counts["low"] * 1
    )
    health_score = max(0.0, min(100.0, 100.0 - deductions))

    report = {
        "total_issues": len(all_issues),
        "severity_counts": severity_counts,
        "agent_counts": agent_counts,
        "health_score": health_score,
        "llm_enhanced": llm_client.available,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "report": report,
        "progress": 1.0,
        "current_step": "Report complete",
        "status": "complete",
    }


# ── Build Audit Graph ───────────────────────────────────────

def create_audit_graph():
    """Create the LangGraph audit pipeline."""
    if not LANGGRAPH_AVAILABLE:
        return None

    graph = StateGraph(AuditState)

    # Add nodes
    graph.add_node("security_scan", security_scan_node)
    graph.add_node("quality_scan", quality_scan_node)
    graph.add_node("completeness_scan", completeness_scan_node)
    graph.add_node("dependency_scan", dependency_scan_node)
    graph.add_node("merge_and_enhance", merge_and_enhance_node)
    graph.add_node("generate_report", generate_report_node)

    # Define edges (sequential pipeline)
    graph.set_entry_point("security_scan")
    graph.add_edge("security_scan", "quality_scan")
    graph.add_edge("quality_scan", "completeness_scan")
    graph.add_edge("completeness_scan", "dependency_scan")
    graph.add_edge("dependency_scan", "merge_and_enhance")
    graph.add_edge("merge_and_enhance", "generate_report")
    graph.add_edge("generate_report", END)

    return graph.compile()


# ── Fallback Sequential Runner ──────────────────────────────

async def run_audit_sequential(state: AuditState) -> AuditState:
    """Fallback: Run all agents sequentially without LangGraph."""
    result = dict(state)

    # Run each agent
    for node_fn in [
        security_scan_node,
        quality_scan_node,
        completeness_scan_node,
        dependency_scan_node,
        merge_and_enhance_node,
        generate_report_node,
    ]:
        updates = await node_fn(result)
        result.update(updates)

    return result


# ── Main Entry Point ────────────────────────────────────────

async def run_audit(
    scan_id: str,
    repo_path: str,
    project_info: dict,
    files: list,
    progress_callback=None,
) -> AuditState:
    """
    Run the full audit pipeline on a repository.

    Args:
        scan_id: Unique scan identifier
        repo_path: Path to the cloned/extracted repository
        project_info: Project metadata (languages, frameworks, etc.)
        files: List of file dicts to analyze
        progress_callback: Optional async callback(progress, step) for updates

    Returns:
        Final AuditState with all issues and report
    """
    initial_state: AuditState = {
        "scan_id": scan_id,
        "repo_path": repo_path,
        "project_info": project_info,
        "files": files,
        "security_issues": [],
        "quality_issues": [],
        "completeness_issues": [],
        "dependency_issues": [],
        "all_issues": [],
        "report": {},
        "status": "scanning",
        "progress": 0.15,
        "current_step": "Starting agent pipeline",
        "error": None,
    }

    if progress_callback:
        await progress_callback(0.15, "Starting agent pipeline")

    try:
        audit_graph = create_audit_graph()

        if audit_graph:
            logger.info(f"[{scan_id}] Running audit with LangGraph pipeline")
            # LangGraph execution
            final_state = None
            async for state in audit_graph.astream(initial_state):
                # LangGraph returns {node_name: state_update}
                for node_name, updates in state.items():
                    if isinstance(updates, dict):
                        initial_state.update(updates)
                        if progress_callback:
                            await progress_callback(
                                updates.get("progress", initial_state["progress"]),
                                updates.get("current_step", initial_state["current_step"]),
                            )
            final_state = initial_state
        else:
            logger.info(f"[{scan_id}] Running audit with sequential pipeline")
            final_state = await run_audit_sequential(initial_state)

        return final_state

    except Exception as e:
        logger.error(f"[{scan_id}] Audit pipeline failed: {e}", exc_info=True)
        initial_state["status"] = "failed"
        initial_state["error"] = str(e)
        return initial_state
