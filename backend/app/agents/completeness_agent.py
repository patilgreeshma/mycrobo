"""
CodeSentinel - Completeness Agent
Detects incomplete implementations: TODOs, missing validation,
empty function bodies, missing error handling, and unfinished features.
"""

import re
from typing import List

from app.agents.base_agent import BaseAgent
from app.utils.llm_client import llm_client


class CompletenessAgent(BaseAgent):
    """Agent that finds incomplete implementations and coding gaps."""

    def __init__(self):
        super().__init__(name="CompletenessAgent", agent_type="completeness")

    async def analyze(self, files: List[dict], project_info: dict) -> List[dict]:
        """Analyze files for completeness issues."""
        all_issues = []

        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            ext = file_info["extension"]

            if ext not in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".cs"):
                continue

            # 1. TODO / FIXME / HACK comments
            all_issues.extend(self._find_todos(content, path))

            # 2. Empty/stub function bodies
            all_issues.extend(self._find_stub_functions(content, path, ext))

            # 3. Missing error handling
            all_issues.extend(self._find_missing_error_handling(content, path, ext))

            # 4. Incomplete implementations
            all_issues.extend(self._find_incomplete_implementations(content, path, ext))

            # 5. Missing input validation
            all_issues.extend(self._find_missing_validation(content, path, ext))

        # 6. LLM-powered completeness analysis
        code_files = [
            f for f in files
            if f["extension"] in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".go")
        ]
        for file_info in code_files[:15]:
            language = project_info.get("primary_language", "unknown")
            llm_issues = await llm_client.analyze_completeness(
                file_info["content"], file_info["path"], language
            )
            all_issues.extend(llm_issues)

        return self._deduplicate(all_issues)

    def _find_todos(self, content: str, file_path: str) -> List[dict]:
        """Find TODO, FIXME, HACK, XXX, and TEMP comments."""
        issues = []
        lines = content.split("\n")

        todo_pattern = re.compile(
            r'(?:#|//|/\*|\*)\s*(TODO|FIXME|HACK|XXX|TEMP|BROKEN|WORKAROUND)\s*:?\s*(.*)',
            re.IGNORECASE
        )

        for line_num, line in enumerate(lines, 1):
            match = todo_pattern.search(line)
            if match:
                tag = match.group(1).upper()
                message = match.group(2).strip() or "No description provided"

                severity_map = {
                    "FIXME": "high",
                    "HACK": "high",
                    "BROKEN": "high",
                    "TODO": "medium",
                    "WORKAROUND": "medium",
                    "XXX": "medium",
                    "TEMP": "low",
                }

                issues.append(self._create_issue(
                    severity=severity_map.get(tag, "medium"),
                    category="todo_comment",
                    title=f"{tag} comment: {message[:80]}",
                    description=(
                        f"A {tag} comment was found indicating unfinished work: \"{message}\". "
                        f"These markers should be resolved before production deployment."
                    ),
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=line.strip()[:200],
                ))

        return issues

    def _find_stub_functions(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Find empty or stub function/method bodies."""
        issues = []
        lines = content.split("\n")

        if ext == ".py":
            # Python: look for `def x(...): pass` or `def x(...): ...`
            func_pattern = re.compile(r'^(\s*)(async\s+)?def\s+(\w+)\s*\(')
            for line_num, line in enumerate(lines, 1):
                match = func_pattern.match(line)
                if match:
                    func_name = match.group(3)
                    # Check next non-empty lines for stub indicators
                    body_lines = []
                    for j in range(line_num, min(line_num + 5, len(lines))):
                        body_line = lines[j].strip()
                        if body_line and not body_line.startswith("#") and not body_line.startswith('"""') and not body_line.startswith("'''"):
                            body_lines.append(body_line)

                    body_text = " ".join(body_lines)
                    if any(stub in body_text for stub in ["pass", "...", "raise NotImplementedError", "return None"]):
                        if func_name not in ("__init__", "__repr__", "__str__"):
                            issues.append(self._create_issue(
                                severity="medium",
                                category="stub_function",
                                title=f"Stub function: '{func_name}()' has no implementation",
                                description=(
                                    f"The function '{func_name}' has a placeholder body (pass, ..., or NotImplementedError). "
                                    f"This indicates an incomplete implementation that needs to be finished."
                                ),
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num + 2,
                                code_snippet="\n".join(lines[line_num - 1:min(line_num + 3, len(lines))]),
                            ))

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # JavaScript/TypeScript: look for empty function bodies
            empty_func = re.compile(r'(?:function\s+\w+|=>\s*)\s*\{\s*\}')
            for line_num, line in enumerate(lines, 1):
                if empty_func.search(line):
                    issues.append(self._create_issue(
                        severity="medium",
                        category="stub_function",
                        title="Empty function body",
                        description="This function has an empty body and needs implementation.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                    ))

        return issues

    def _find_missing_error_handling(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Find code that should have error handling but doesn't."""
        issues = []
        lines = content.split("\n")

        if ext == ".py":
            # Bare except clauses
            bare_except = re.compile(r'^\s*except\s*:\s*$')
            broad_except = re.compile(r'^\s*except\s+(?:Exception|BaseException)\s*(?:as\s+\w+)?:\s*$')

            for line_num, line in enumerate(lines, 1):
                if bare_except.match(line):
                    issues.append(self._create_issue(
                        severity="high",
                        category="bare_except",
                        title="Bare except clause catches all exceptions",
                        description=(
                            "Using 'except:' without specifying an exception type catches ALL exceptions, "
                            "including SystemExit, KeyboardInterrupt, and MemoryError. This can mask "
                            "real bugs and make debugging extremely difficult."
                        ),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip(),
                    ))
                elif broad_except.match(line):
                    # Check if the except block just passes
                    next_line = lines[line_num].strip() if line_num < len(lines) else ""
                    if next_line in ("pass", "..."):
                        issues.append(self._create_issue(
                            severity="high",
                            category="swallowed_exception",
                            title="Exception caught and silently swallowed",
                            description=(
                                "An exception is caught but completely ignored (pass). "
                                "This hides errors that should be logged or handled properly."
                            ),
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num + 1,
                            code_snippet=f"{line.strip()}\n    {next_line}",
                        ))

            # Risky operations without try/except
            risky_ops = re.compile(
                r'(?:open\s*\(|\.read\(|\.write\(|requests\.\w+\(|urllib|'
                r'json\.loads?\(|\.connect\(|\.execute\()',
            )
            in_try = False
            for line_num, line in enumerate(lines, 1):
                stripped = line.strip()
                if stripped.startswith("try:"):
                    in_try = True
                elif stripped.startswith(("except", "finally:")):
                    pass
                elif not stripped.startswith(" ") and not stripped.startswith("\t"):
                    if stripped and not stripped.startswith("#"):
                        in_try = False

                if risky_ops.search(stripped) and not in_try:
                    issues.append(self._create_issue(
                        severity="medium",
                        category="missing_error_handling",
                        title="Risky operation without error handling",
                        description=(
                            "This operation (file I/O, network request, or parsing) can fail "
                            "at runtime but is not wrapped in a try/except block. Add proper "
                            "error handling to prevent unexpected crashes."
                        ),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped[:200],
                    ))

        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            # Empty catch blocks
            empty_catch = re.compile(r'catch\s*\([^)]*\)\s*\{\s*\}')
            for line_num, line in enumerate(lines, 1):
                if empty_catch.search(line) or (
                    "catch" in line and line_num < len(lines) and lines[line_num].strip() == "}"
                ):
                    issues.append(self._create_issue(
                        severity="high",
                        category="empty_catch",
                        title="Empty catch block silently swallows errors",
                        description="Errors caught in this block are completely ignored. At minimum, log the error.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                    ))

        return issues

    def _find_incomplete_implementations(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Find NotImplementedError, placeholder returns, and similar patterns."""
        issues = []
        lines = content.split("\n")

        patterns = [
            (re.compile(r'raise\s+NotImplementedError', re.IGNORECASE), "NotImplementedError raised", "high"),
            (re.compile(r'throw\s+new\s+Error\s*\(\s*["\']not\s+implemented', re.IGNORECASE), "Not implemented error thrown", "high"),
            (re.compile(r'#\s*placeholder', re.IGNORECASE), "Placeholder comment", "medium"),
            (re.compile(r'//\s*placeholder', re.IGNORECASE), "Placeholder comment", "medium"),
            (re.compile(r'return\s+(?:None|null|undefined|nil)\s*#.*(?:temp|placeholder|fixme|todo)', re.IGNORECASE), "Placeholder return value", "medium"),
        ]

        for line_num, line in enumerate(lines, 1):
            for pattern, title, severity in patterns:
                if pattern.search(line):
                    issues.append(self._create_issue(
                        severity=severity,
                        category="incomplete_implementation",
                        title=title,
                        description=f"This code contains an incomplete implementation marker at line {line_num}.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                    ))

        return issues

    def _find_missing_validation(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Find API endpoints and functions that lack input validation."""
        issues = []
        lines = content.split("\n")

        if ext == ".py":
            # FastAPI/Flask/Django endpoints without validation
            endpoint_pattern = re.compile(
                r'@(?:app|router|api_view)\.\s*(?:get|post|put|patch|delete)\s*\('
            )
            for line_num, line in enumerate(lines, 1):
                if endpoint_pattern.search(line):
                    # Check the next 15 lines for validation patterns
                    body = "\n".join(lines[line_num:min(line_num + 15, len(lines))])
                    has_validation = any(
                        pattern in body.lower()
                        for pattern in ["validate", "pydantic", "serializer", "schema", "form.is_valid", "if not"]
                    )
                    if not has_validation:
                        issues.append(self._create_issue(
                            severity="medium",
                            category="missing_validation",
                            title="API endpoint may lack input validation",
                            description=(
                                "This API endpoint does not appear to validate its input. "
                                "Missing validation can lead to unexpected behavior, "
                                "data corruption, or security vulnerabilities."
                            ),
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip()[:200],
                        ))

        elif ext in (".js", ".ts"):
            # Express.js routes without validation
            route_pattern = re.compile(r'(?:router|app)\.(?:get|post|put|patch|delete)\s*\(')
            for line_num, line in enumerate(lines, 1):
                if route_pattern.search(line):
                    body = "\n".join(lines[line_num:min(line_num + 15, len(lines))])
                    has_validation = any(
                        pattern in body.lower()
                        for pattern in ["validate", "joi", "zod", "yup", "schema", "if (!req.body", "if (!req.params"]
                    )
                    if not has_validation:
                        issues.append(self._create_issue(
                            severity="medium",
                            category="missing_validation",
                            title="Route handler may lack input validation",
                            description="This route handler does not appear to validate its input parameters.",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            code_snippet=line.strip()[:200],
                        ))

        return issues

    def _deduplicate(self, issues: List[dict]) -> List[dict]:
        """Remove duplicate issues."""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.get("file_path"), issue.get("line_start"), issue.get("category"))
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        return unique
