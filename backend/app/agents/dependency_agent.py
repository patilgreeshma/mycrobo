"""
CodeSentinel - Dependency Agent
Analyzes project dependencies for known vulnerabilities,
outdated versions, and security issues.
"""

import re
import json
from typing import List, Dict, Optional

from app.agents.base_agent import BaseAgent
from app.utils.llm_client import llm_client


# Known vulnerable package patterns (simplified for hackathon)
KNOWN_VULNERABLE_PACKAGES = {
    "python": {
        "django": {"below": "4.2", "severity": "high", "cve": "Multiple CVEs in Django < 4.2"},
        "flask": {"below": "2.3", "severity": "medium", "cve": "Security fixes in Flask 2.3+"},
        "requests": {"below": "2.31", "severity": "medium", "cve": "CVE-2023-32681: Unintended data leak"},
        "urllib3": {"below": "2.0", "severity": "high", "cve": "Multiple security fixes in urllib3 2.0"},
        "pyyaml": {"below": "6.0", "severity": "high", "cve": "CVE-2020-14343: Arbitrary code execution"},
        "pillow": {"below": "10.0", "severity": "high", "cve": "Multiple buffer overflow vulnerabilities"},
        "cryptography": {"below": "41.0", "severity": "high", "cve": "Multiple security fixes"},
        "jinja2": {"below": "3.1.2", "severity": "medium", "cve": "XSS vulnerability in older versions"},
        "sqlalchemy": {"below": "2.0", "severity": "low", "cve": "Security improvements in 2.0"},
        "numpy": {"below": "1.22", "severity": "medium", "cve": "Buffer overflow fixes"},
    },
    "node": {
        "express": {"below": "4.18", "severity": "medium", "cve": "Various security fixes"},
        "lodash": {"below": "4.17.21", "severity": "high", "cve": "CVE-2021-23337: Command injection"},
        "axios": {"below": "1.6", "severity": "medium", "cve": "CSRF and SSRF vulnerabilities"},
        "jsonwebtoken": {"below": "9.0", "severity": "high", "cve": "CVE-2022-23529: Token forgery"},
        "minimist": {"below": "1.2.6", "severity": "high", "cve": "Prototype pollution"},
        "node-fetch": {"below": "3.3", "severity": "medium", "cve": "Data exposure vulnerability"},
        "passport": {"below": "0.6", "severity": "medium", "cve": "Session fixation vulnerability"},
        "mongoose": {"below": "7.0", "severity": "medium", "cve": "Prototype pollution fixes"},
        "helmet": {"below": "7.0", "severity": "low", "cve": "Security header improvements"},
    },
}

# Security-sensitive packages that should be present
RECOMMENDED_SECURITY_PACKAGES = {
    "python": {
        "web_app": ["python-dotenv", "cryptography"],
        "api": ["pydantic", "python-jose", "passlib"],
    },
    "node": {
        "web_app": ["helmet", "cors", "express-rate-limit"],
        "api": ["jsonwebtoken", "bcrypt", "express-validator"],
    },
}


class DependencyAgent(BaseAgent):
    """Agent that analyzes project dependencies for vulnerabilities."""

    def __init__(self):
        super().__init__(name="DependencyAgent", agent_type="dependency")

    async def analyze(self, files: List[dict], project_info: dict) -> List[dict]:
        """Analyze project dependencies for vulnerabilities and issues."""
        all_issues = []
        dep_files = project_info.get("dependency_files", [])

        if not dep_files:
            all_issues.append(self._create_issue(
                severity="medium",
                category="no_dependencies_file",
                title="No dependency management file found",
                description=(
                    "No package manager file (requirements.txt, package.json, etc.) was found. "
                    "Without explicit dependency management, it's impossible to track and update "
                    "dependencies or identify vulnerable versions."
                ),
            ))
            return all_issues

        for dep_file in dep_files:
            dep_type = dep_file.get("type", "")
            content = dep_file.get("content", "")
            path = dep_file.get("path", "")

            if dep_type.startswith("python"):
                all_issues.extend(self._analyze_python_deps(content, path, dep_type))
            elif dep_type.startswith("node"):
                all_issues.extend(self._analyze_node_deps(content, path))

            # Check for lockfile
            all_issues.extend(self._check_lockfile(dep_files, dep_type, path))

        # LLM-enhanced dependency analysis
        if llm_client.available and dep_files:
            all_issues.extend(await self._llm_dependency_analysis(dep_files, project_info))

        return all_issues

    def _analyze_python_deps(self, content: str, file_path: str, dep_type: str) -> List[dict]:
        """Analyze Python dependency files."""
        issues = []

        if dep_type == "python-pip":
            issues.extend(self._check_requirements_txt(content, file_path))
        elif dep_type == "python-pyproject":
            issues.extend(self._check_pyproject_toml(content, file_path))

        return issues

    def _check_requirements_txt(self, content: str, file_path: str) -> List[dict]:
        """Check requirements.txt for issues."""
        issues = []
        lines = content.strip().split("\n")
        unpinned_count = 0

        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            # Parse package name and version
            match = re.match(r'^([a-zA-Z0-9_-]+)\s*(?:([><=!~]+)\s*([0-9][0-9.]*))?', line)
            if not match:
                continue

            pkg_name = match.group(1).lower()
            operator = match.group(2)
            version = match.group(3)

            # Check for unpinned dependencies
            if not version:
                unpinned_count += 1

            # Check for known vulnerable versions
            if pkg_name in KNOWN_VULNERABLE_PACKAGES.get("python", {}):
                vuln_info = KNOWN_VULNERABLE_PACKAGES["python"][pkg_name]
                if version and self._version_below(version, vuln_info["below"]):
                    issues.append(self._create_issue(
                        severity=vuln_info["severity"],
                        category="vulnerable_dependency",
                        title=f"Vulnerable dependency: {pkg_name} {version}",
                        description=(
                            f"Package '{pkg_name}' version {version} has known vulnerabilities. "
                            f"{vuln_info['cve']}. Upgrade to version {vuln_info['below']}+."
                        ),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line,
                        suggestion=f"Upgrade {pkg_name} to version {vuln_info['below']} or later.",
                        suggested_code=f"{pkg_name}>={vuln_info['below']}",
                        original_code=line,
                    ))

            # Check for >= with no upper bound
            if operator == ">=" and version:
                issues.append(self._create_issue(
                    severity="low",
                    category="unpinned_upper_bound",
                    title=f"No upper version bound for {pkg_name}",
                    description=(
                        f"Package '{pkg_name}' has a lower bound ({operator}{version}) but no upper bound. "
                        f"A major version bump could introduce breaking changes."
                    ),
                    file_path=file_path,
                    line_start=line_num,
                    line_end=line_num,
                    code_snippet=line,
                ))

        # Report if many dependencies are unpinned
        if unpinned_count >= 3:
            issues.append(self._create_issue(
                severity="medium",
                category="unpinned_dependencies",
                title=f"{unpinned_count} dependencies without version pinning",
                description=(
                    f"Found {unpinned_count} packages without version constraints. "
                    f"This can lead to non-reproducible builds and unexpected breaking changes. "
                    f"Pin all dependencies to specific versions."
                ),
                file_path=file_path,
            ))

        return issues

    def _check_pyproject_toml(self, content: str, file_path: str) -> List[dict]:
        """Check pyproject.toml for dependency issues."""
        issues = []
        # Basic check for dependencies section
        if "[project.dependencies]" not in content and "dependencies" not in content:
            return issues

        # Extract dependency lines
        in_deps = False
        for line_num, line in enumerate(content.split("\n"), 1):
            stripped = line.strip()
            if "dependencies" in stripped and "=" in stripped:
                in_deps = True
                continue
            if in_deps:
                if stripped.startswith("[") or (stripped and not stripped.startswith('"') and not stripped.startswith("'")):
                    in_deps = False
                    continue
                # Extract package name
                match = re.search(r'"([a-zA-Z0-9_-]+)', stripped)
                if match:
                    pkg_name = match.group(1).lower()
                    if pkg_name in KNOWN_VULNERABLE_PACKAGES.get("python", {}):
                        vuln_info = KNOWN_VULNERABLE_PACKAGES["python"][pkg_name]
                        issues.append(self._create_issue(
                            severity="info",
                            category="dependency_check",
                            title=f"Check dependency: {pkg_name}",
                            description=f"Ensure '{pkg_name}' is at version {vuln_info['below']}+. {vuln_info['cve']}",
                            file_path=file_path,
                            line_start=line_num,
                            code_snippet=stripped,
                        ))

        return issues

    def _analyze_node_deps(self, content: str, file_path: str) -> List[dict]:
        """Analyze package.json for dependency issues."""
        issues = []

        try:
            pkg = json.loads(content)
        except json.JSONDecodeError:
            issues.append(self._create_issue(
                severity="high",
                category="invalid_package_json",
                title="Invalid package.json",
                description="The package.json file contains invalid JSON and cannot be parsed.",
                file_path=file_path,
            ))
            return issues

        all_deps = {}
        all_deps.update(pkg.get("dependencies", {}))
        all_deps.update(pkg.get("devDependencies", {}))

        for pkg_name, version_spec in all_deps.items():
            clean_name = pkg_name.lower().split("/")[-1]  # Handle scoped packages

            # Strip version prefix
            version = re.sub(r'^[~^>=<]*', '', version_spec)

            if clean_name in KNOWN_VULNERABLE_PACKAGES.get("node", {}):
                vuln_info = KNOWN_VULNERABLE_PACKAGES["node"][clean_name]
                if version and self._version_below(version, vuln_info["below"]):
                    issues.append(self._create_issue(
                        severity=vuln_info["severity"],
                        category="vulnerable_dependency",
                        title=f"Vulnerable dependency: {pkg_name}@{version_spec}",
                        description=(
                            f"Package '{pkg_name}' version {version_spec} has known vulnerabilities. "
                            f"{vuln_info['cve']}. Upgrade to version {vuln_info['below']}+."
                        ),
                        file_path=file_path,
                        code_snippet=f'"{pkg_name}": "{version_spec}"',
                        suggestion=f"Run: npm install {pkg_name}@latest",
                        suggested_code=f'"{pkg_name}": "^{vuln_info["below"]}"',
                        original_code=f'"{pkg_name}": "{version_spec}"',
                    ))

            # Check for wildcard versions
            if version_spec in ("*", "latest"):
                issues.append(self._create_issue(
                    severity="high",
                    category="wildcard_dependency",
                    title=f"Wildcard version for {pkg_name}",
                    description=f"Using '{version_spec}' for {pkg_name} is dangerous and non-reproducible.",
                    file_path=file_path,
                    code_snippet=f'"{pkg_name}": "{version_spec}"',
                ))

        # Check if security packages are missing
        deps_set = set(all_deps.keys())
        if "express" in deps_set:
            for recommended in ["helmet", "cors", "express-rate-limit"]:
                if recommended not in deps_set:
                    issues.append(self._create_issue(
                        severity="medium",
                        category="missing_security_package",
                        title=f"Missing recommended security package: {recommended}",
                        description=f"Your Express app should use '{recommended}' for better security.",
                        file_path=file_path,
                        suggestion=f"Run: npm install {recommended}",
                    ))

        # Check for scripts
        scripts = pkg.get("scripts", {})
        if not scripts.get("test"):
            issues.append(self._create_issue(
                severity="low",
                category="no_test_script",
                title="No test script defined",
                description="No 'test' script found in package.json. Add tests for code reliability.",
                file_path=file_path,
            ))

        return issues

    def _check_lockfile(self, dep_files: List[dict], dep_type: str, file_path: str) -> List[dict]:
        """Check if a lockfile exists for the dependency manager."""
        issues = []
        file_names = {d["path"].split("/")[-1] for d in dep_files}

        lockfile_map = {
            "python-pip": ["requirements.txt"],  # Already a pinned file
            "python-pipenv": ["Pipfile.lock"],
            "node-npm": ["package-lock.json"],
            "node-yarn": ["yarn.lock"],
            "node-pnpm": ["pnpm-lock.yaml"],
        }

        expected_locks = lockfile_map.get(dep_type, [])
        if dep_type == "node-npm" and "package-lock.json" not in file_names and "yarn.lock" not in file_names:
            issues.append(self._create_issue(
                severity="medium",
                category="missing_lockfile",
                title="No package lock file found",
                description=(
                    "No package-lock.json or yarn.lock was found. Without a lockfile, "
                    "builds are non-deterministic and may install different dependency versions."
                ),
                file_path=file_path,
                suggestion="Run 'npm install' to generate package-lock.json",
            ))

        return issues

    async def _llm_dependency_analysis(self, dep_files: List[dict], project_info: dict) -> List[dict]:
        """Use LLM for deeper dependency analysis."""
        if not llm_client.available:
            return []

        # Combine dependency file contents for analysis
        dep_summary = "\n\n".join(
            f"=== {d['path']} ===\n{d['content'][:2000]}"
            for d in dep_files[:5]
        )

        prompt = f"""Analyze these project dependency files for security and best practice issues.
Focus on issues NOT covered by simple version checking.

{dep_summary}

Look for:
- Conflicting dependencies
- Dependencies that should be devDependencies (or vice versa)
- Known malicious or typo-squatting packages
- Missing essential security packages for the detected framework
- Overly permissive version ranges

Return a JSON array of issues:
[{{
  "severity": "critical|high|medium|low",
  "category": "<category_slug>",
  "title": "<title>",
  "description": "<description>",
  "suggestion": "<how to fix>"
}}]

If no issues found, return []. Return ONLY the JSON array."""

        try:
            response = llm_client.model.generate_content(prompt)
            issues = json.loads(response.text)
            for issue in issues:
                issue["agent_type"] = "dependency"
            return issues
        except Exception as e:
            self.logger.warning(f"LLM dependency analysis failed: {e}")
            return []

    @staticmethod
    def _version_below(current: str, minimum: str) -> bool:
        """Compare two version strings. Returns True if current < minimum."""
        try:
            current_parts = [int(x) for x in current.split(".")[:3]]
            minimum_parts = [int(x) for x in minimum.split(".")[:3]]

            # Pad to equal length
            while len(current_parts) < 3:
                current_parts.append(0)
            while len(minimum_parts) < 3:
                minimum_parts.append(0)

            return current_parts < minimum_parts
        except (ValueError, AttributeError):
            return False
