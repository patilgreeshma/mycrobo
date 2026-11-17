"""
CodeSentinel - Code Quality Agent
Detects code quality issues: duplicated code, excessive complexity,
AI-generated slop, dead code, and anti-patterns.
"""

import re
import hashlib
from typing import List, Dict, Set
from collections import defaultdict

from app.agents.base_agent import BaseAgent
from app.utils.llm_client import llm_client


class QualityAgent(BaseAgent):
    """Agent that detects code quality issues and AI slop."""

    def __init__(self):
        super().__init__(name="QualityAgent", agent_type="quality")

    async def analyze(self, files: List[dict], project_info: dict) -> List[dict]:
        """Analyze code quality across all files."""
        all_issues = []

        # 1. Duplicate code detection (cross-file)
        all_issues.extend(self._detect_duplicates(files))

        # 2. Per-file analysis
        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            ext = file_info["extension"]

            if ext not in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".cs"):
                continue

            # Complexity analysis
            all_issues.extend(self._check_complexity(content, path))

            # Dead code detection
            all_issues.extend(self._detect_dead_code(content, path, ext))

            # AI slop detection
            all_issues.extend(self._detect_ai_slop(content, path))

            # Long functions
            all_issues.extend(self._check_function_length(content, path, ext))

        # 3. LLM-powered quality analysis (max 3 files to respect rate limits)
        if llm_client.available:
            code_files = [
                f for f in files
                if f["extension"] in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".go")
            ]
            for file_info in code_files[:3]:
                language = project_info.get("primary_language", "unknown")
                llm_issues = await llm_client.analyze_quality(
                    file_info["content"], file_info["path"], language
                )
                all_issues.extend(llm_issues)

        return self._deduplicate(all_issues)

    def _detect_duplicates(self, files: List[dict]) -> List[dict]:
        """Detect duplicated code blocks across files using hashing."""
        issues = []
        block_hashes: Dict[str, List[dict]] = defaultdict(list)
        BLOCK_SIZE = 6  # Minimum lines to consider as a "block"

        for file_info in files:
            ext = file_info["extension"]
            if ext not in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".go", ".rb", ".rs"):
                continue

            lines = file_info["content"].split("\n")

            for i in range(len(lines) - BLOCK_SIZE + 1):
                block = lines[i:i + BLOCK_SIZE]
                # Normalize whitespace for comparison
                normalized = "\n".join(line.strip() for line in block if line.strip())

                # Skip blocks that are too short or just whitespace/braces
                if len(normalized) < 60:
                    continue
                if all(c in "{}()[];,\n " for c in normalized):
                    continue

                block_hash = hashlib.md5(normalized.encode()).hexdigest()
                block_hashes[block_hash].append({
                    "file": file_info["path"],
                    "line": i + 1,
                    "content": "\n".join(block),
                })

        # Report blocks that appear in multiple locations
        for _hash, locations in block_hashes.items():
            if len(locations) >= 2:
                # Deduplicate within same file (overlapping blocks)
                unique_locs = []
                seen_positions = set()
                for loc in locations:
                    pos = (loc["file"], loc["line"])
                    if pos not in seen_positions:
                        seen_positions.add(pos)
                        unique_locs.append(loc)

                if len(unique_locs) >= 2:
                    loc_descriptions = [
                        f"{loc['file']}:{loc['line']}" for loc in unique_locs[:5]
                    ]
                    issues.append(self._create_issue(
                        severity="medium",
                        category="duplicate_code",
                        title="Duplicated code block detected",
                        description=(
                            f"Nearly identical code blocks found in {len(unique_locs)} locations: "
                            f"{', '.join(loc_descriptions)}. "
                            f"Consider extracting this into a reusable function or utility."
                        ),
                        file_path=unique_locs[0]["file"],
                        line_start=unique_locs[0]["line"],
                        line_end=unique_locs[0]["line"] + BLOCK_SIZE,
                        code_snippet=unique_locs[0]["content"][:300],
                    ))

        return issues[:20]  # Cap duplicate reports

    def _check_complexity(self, content: str, file_path: str) -> List[dict]:
        """Detect overly complex code (deep nesting, high cyclomatic complexity)."""
        issues = []
        lines = content.split("\n")
        max_nesting = 0
        current_nesting = 0
        max_nesting_line = 0

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Count nesting by indentation or braces
            indent_level = (len(line) - len(line.lstrip())) // 4  # Assuming 4-space indent

            # Also count opening/closing braces
            brace_open = stripped.count("{") - stripped.count("}")
            current_nesting += brace_open

            effective_nesting = max(indent_level, current_nesting)

            if effective_nesting > max_nesting:
                max_nesting = effective_nesting
                max_nesting_line = line_num

        if max_nesting >= 5:
            severity = "high" if max_nesting >= 7 else "medium"
            issues.append(self._create_issue(
                severity=severity,
                category="excessive_complexity",
                title=f"Deeply nested code ({max_nesting} levels deep)",
                description=(
                    f"Code reaches {max_nesting} levels of nesting, making it very hard "
                    f"to read and maintain. Consider using early returns, guard clauses, "
                    f"or extracting nested logic into separate functions."
                ),
                file_path=file_path,
                line_start=max_nesting_line,
                line_end=max_nesting_line,
                code_snippet=lines[max(0, max_nesting_line - 1):min(len(lines), max_nesting_line + 2)].__str__(),
            ))

        return issues

    def _detect_dead_code(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Detect unused imports and variables."""
        issues = []
        lines = content.split("\n")

        if ext == ".py":
            issues.extend(self._detect_unused_python_imports(content, file_path, lines))
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            issues.extend(self._detect_unused_js_imports(content, file_path, lines))

        return issues

    def _detect_unused_python_imports(self, content: str, file_path: str, lines: List[str]) -> List[dict]:
        """Detect unused Python imports."""
        issues = []
        import_pattern = re.compile(r'^(?:from\s+\S+\s+)?import\s+(.+)$')

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            match = import_pattern.match(stripped)
            if not match:
                continue

            imported_names_raw = match.group(1)
            # Handle "import x as y" and "from x import a, b, c"
            names = []
            for part in imported_names_raw.split(","):
                part = part.strip()
                if " as " in part:
                    names.append(part.split(" as ")[1].strip())
                else:
                    names.append(part.split(".")[-1].strip())

            # Check if each imported name is used elsewhere in the file
            remaining_content = "\n".join(lines[line_num:])
            for name in names:
                if name and name != "*" and not re.search(r'\b' + re.escape(name) + r'\b', remaining_content):
                    issues.append(self._create_issue(
                        severity="low",
                        category="unused_import",
                        title=f"Unused import: '{name}'",
                        description=f"The import '{name}' is never used in the rest of the file. Remove it to keep the code clean.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=stripped,
                    ))

        return issues

    def _detect_unused_js_imports(self, content: str, file_path: str, lines: List[str]) -> List[dict]:
        """Detect unused JavaScript/TypeScript imports."""
        issues = []
        import_pattern = re.compile(r'import\s+(?:\{([^}]+)\}|(\w+))\s+from')

        for line_num, line in enumerate(lines, 1):
            match = import_pattern.search(line.strip())
            if not match:
                continue

            if match.group(1):
                names = [n.strip().split(" as ")[-1].strip() for n in match.group(1).split(",")]
            elif match.group(2):
                names = [match.group(2)]
            else:
                continue

            remaining_content = "\n".join(lines[line_num:])
            for name in names:
                if name and not re.search(r'\b' + re.escape(name) + r'\b', remaining_content):
                    issues.append(self._create_issue(
                        severity="low",
                        category="unused_import",
                        title=f"Unused import: '{name}'",
                        description=f"The import '{name}' is never used in the rest of the file.",
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip(),
                    ))

        return issues

    def _detect_ai_slop(self, content: str, file_path: str) -> List[dict]:
        """Detect potential AI-generated low-quality code (slop)."""
        issues = []
        lines = content.split("\n")

        # Pattern 1: Comments that just repeat the code
        comment_patterns = [
            (r'#\s*(?:import|set|define|create|initialize|get|return)\s+(?:the\s+)?(\w+)', 'python'),
            (r'//\s*(?:import|set|define|create|initialize|get|return)\s+(?:the\s+)?(\w+)', 'js'),
        ]

        redundant_comment_count = 0
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # Check if a comment is redundant (just describes the next line literally)
            if line_num < len(lines):
                next_line = lines[line_num].strip() if line_num < len(lines) else ""
                if (stripped.startswith("#") or stripped.startswith("//")):
                    comment_text = re.sub(r'^[#/]+\s*', '', stripped).lower()
                    code_text = re.sub(r'[^a-z0-9\s]', ' ', next_line.lower())
                    # If comment words mostly match the next line's words
                    comment_words = set(comment_text.split())
                    code_words = set(code_text.split())
                    if len(comment_words) >= 3 and len(comment_words & code_words) / len(comment_words) > 0.6:
                        redundant_comment_count += 1

        if redundant_comment_count >= 5:
            issues.append(self._create_issue(
                severity="low",
                category="ai_slop",
                title="Excessive redundant comments (possible AI-generated code)",
                description=(
                    f"Found {redundant_comment_count} comments that simply restate what the code does. "
                    f"This is a common pattern in AI-generated code. Comments should explain WHY, "
                    f"not WHAT the code does."
                ),
                file_path=file_path,
                line_start=1,
            ))

        # Pattern 2: Excessive docstrings that add no value
        trivial_docstring_pattern = re.compile(
            r'"""(?:This (?:function|method|class) )?(?:returns?|gets?|sets?|creates?|initializes?)\s+(?:the\s+)?(\w+)\.?"""',
            re.IGNORECASE
        )
        trivial_docs = trivial_docstring_pattern.findall(content)
        if len(trivial_docs) >= 4:
            issues.append(self._create_issue(
                severity="info",
                category="ai_slop",
                title="Multiple trivial docstrings detected",
                description=(
                    f"Found {len(trivial_docs)} docstrings that add no information beyond "
                    f"the function name. Consider writing meaningful documentation that "
                    f"explains parameters, return values, and edge cases."
                ),
                file_path=file_path,
                line_start=1,
            ))

        return issues

    def _check_function_length(self, content: str, file_path: str, ext: str) -> List[dict]:
        """Detect overly long functions."""
        issues = []

        if ext == ".py":
            func_pattern = re.compile(r'^([ \t]*)(def|async\s+def)\s+(\w+)\s*\(', re.MULTILINE)
        elif ext in (".js", ".ts", ".jsx", ".tsx"):
            func_pattern = re.compile(r'(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>|(\w+)\s*\([^)]*\)\s*\{)', re.MULTILINE)
        elif ext == ".java":
            func_pattern = re.compile(r'(?:public|private|protected|static|\s)*\s+\w+\s+(\w+)\s*\(', re.MULTILINE)
        else:
            return issues

        lines = content.split("\n")
        matches = list(func_pattern.finditer(content))

        for match in matches:
            func_line = content[:match.start()].count("\n") + 1
            # Estimate function end (next function or end of file)
            func_end = len(lines)
            for next_match in matches:
                next_line = content[:next_match.start()].count("\n") + 1
                if next_line > func_line:
                    func_end = next_line - 1
                    break

            func_length = func_end - func_line

            if func_length > 100:
                func_name = match.group(1) or match.group(2) or match.group(3) or "unknown"
                if hasattr(match, 'group') and match.lastindex:
                    for i in range(1, match.lastindex + 1):
                        if match.group(i):
                            func_name = match.group(i)
                            break

                severity = "high" if func_length > 200 else "medium"
                issues.append(self._create_issue(
                    severity=severity,
                    category="long_function",
                    title=f"Function too long ({func_length} lines)",
                    description=(
                        f"Function '{func_name}' is {func_length} lines long. "
                        f"Long functions are harder to understand, test, and maintain. "
                        f"Consider breaking it into smaller, focused functions."
                    ),
                    file_path=file_path,
                    line_start=func_line,
                    line_end=func_end,
                ))

        return issues

    def _deduplicate(self, issues: List[dict]) -> List[dict]:
        """Remove duplicate issues."""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.get("file_path"), issue.get("line_start"), issue.get("category"), issue.get("title", "")[:50])
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        return unique
