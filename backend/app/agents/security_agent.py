"""
CodeSentinel - Security Agent
Detects security vulnerabilities: hardcoded secrets, SQL injection,
XSS, path traversal, insecure auth, and more.
Combines regex-based static analysis with optional LLM deep analysis.
"""

import re
from typing import List

from app.agents.base_agent import BaseAgent
from app.utils.llm_client import llm_client


# ── Regex patterns for secret detection ──────────────────────

SECRET_PATTERNS = [
    {
        "name": "AWS Access Key",
        "pattern": r'(?:AKIA[0-9A-Z]{16})',
        "severity": "critical",
    },
    {
        "name": "AWS Secret Key",
        "pattern": r'(?:aws_secret_access_key|aws_secret)\s*[=:]\s*["\']?([A-Za-z0-9/+=]{40})',
        "severity": "critical",
    },
    {
        "name": "Generic API Key",
        "pattern": r'(?:api[_-]?key|apikey)\s*[=:]\s*["\']([A-Za-z0-9_\-]{20,})["\']',
        "severity": "critical",
    },
    {
        "name": "Generic Secret",
        "pattern": r'(?:secret|token|password|passwd|pwd)\s*[=:]\s*["\']([^"\']{8,})["\']',
        "severity": "critical",
    },
    {
        "name": "Private Key",
        "pattern": r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----',
        "severity": "critical",
    },
    {
        "name": "GitHub Token",
        "pattern": r'(?:ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{82})',
        "severity": "critical",
    },
    {
        "name": "JWT Token",
        "pattern": r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}',
        "severity": "high",
    },
    {
        "name": "Database URL with Credentials",
        "pattern": r'(?:mysql|postgres|postgresql|mongodb|redis):\/\/[^:]+:[^@]+@',
        "severity": "critical",
    },
    {
        "name": "Slack Webhook",
        "pattern": r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+',
        "severity": "high",
    },
    {
        "name": "Stripe API Key",
        "pattern": r'(?:sk_live_|pk_live_|sk_test_|pk_test_)[A-Za-z0-9]{20,}',
        "severity": "critical",
    },
    {
        "name": "Google API Key",
        "pattern": r'AIza[0-9A-Za-z_-]{35}',
        "severity": "critical",
    },
]

# ── SQL Injection patterns ───────────────────────────────────

SQL_INJECTION_PATTERNS = [
    {
        "name": "String concatenation in SQL",
        "pattern": r'(?:execute|cursor\.execute|query|raw|rawQuery)\s*\(\s*["\'].*?\%s.*?["\'].*?\%|'
                   r'(?:execute|cursor\.execute|query)\s*\(\s*(?:f["\']|["\'].*?\{)',
        "severity": "high",
    },
    {
        "name": "String format in SQL query",
        "pattern": r'(?:SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER)\s+.*?(?:\.format\(|%\s*\(|\+\s*(?:str\()?[a-zA-Z_])',
        "severity": "high",
    },
    {
        "name": "F-string in SQL query",
        "pattern": r'(?:f["\'])(?:SELECT|INSERT|UPDATE|DELETE|DROP)\s+.*?\{',
        "severity": "high",
    },
]

# ── Insecure practices ──────────────────────────────────────

INSECURE_PATTERNS = [
    {
        "name": "Insecure hash algorithm (MD5)",
        "pattern": r'(?:md5|MD5)\s*\(',
        "severity": "medium",
        "category": "insecure_crypto",
        "description": "MD5 is cryptographically broken and should not be used for security purposes.",
    },
    {
        "name": "Insecure hash algorithm (SHA1)",
        "pattern": r'(?:sha1|SHA1)\s*\(',
        "severity": "medium",
        "category": "insecure_crypto",
        "description": "SHA-1 is deprecated for security use. Use SHA-256 or SHA-3 instead.",
    },
    {
        "name": "Disabled SSL verification",
        "pattern": r'verify\s*=\s*False|VERIFY_NONE|SSL_VERIFYPEER.*?0|rejectUnauthorized.*?false',
        "severity": "high",
        "category": "insecure_ssl",
        "description": "SSL/TLS verification is disabled, allowing man-in-the-middle attacks.",
    },
    {
        "name": "Hardcoded IP address",
        "pattern": r'(?:host|server|url)\s*[=:]\s*["\'](?:\d{1,3}\.){3}\d{1,3}["\']',
        "severity": "low",
        "category": "hardcoded_config",
        "description": "IP addresses should not be hardcoded. Use environment variables or config files.",
    },
    {
        "name": "Debug mode enabled",
        "pattern": r'(?:DEBUG|debug)\s*[=:]\s*(?:True|true|1|"true"|\'true\')',
        "severity": "medium",
        "category": "debug_enabled",
        "description": "Debug mode should not be enabled in production. Use environment variables.",
    },
    {
        "name": "eval() usage",
        "pattern": r'\beval\s*\(',
        "severity": "high",
        "category": "code_injection",
        "description": "eval() executes arbitrary code and is a major security risk.",
    },
    {
        "name": "Unsafe deserialization (pickle)",
        "pattern": r'pickle\.loads?\s*\(|yaml\.(?:load|unsafe_load)\s*\(',
        "severity": "high",
        "category": "unsafe_deserialization",
        "description": "Deserializing untrusted data can lead to arbitrary code execution.",
    },
    {
        "name": "Command injection risk",
        "pattern": r'os\.system\s*\(|subprocess\.call\s*\(\s*["\']|subprocess\.Popen\s*\(\s*["\'].*?shell\s*=\s*True',
        "severity": "high",
        "category": "command_injection",
        "description": "Shell commands with user input can lead to command injection attacks.",
    },
    {
        "name": "CORS wildcard",
        "pattern": r'(?:Access-Control-Allow-Origin|cors_origin|allow_origins?).*?\*',
        "severity": "medium",
        "category": "cors_misconfiguration",
        "description": "Wildcard CORS allows any domain to make requests to your API.",
    },
]


class SecurityAgent(BaseAgent):
    """Agent that detects security vulnerabilities in source code."""

    def __init__(self):
        super().__init__(name="SecurityAgent", agent_type="security")

    async def analyze(self, files: List[dict], project_info: dict) -> List[dict]:
        """Scan all files for security vulnerabilities."""
        all_issues = []

        for file_info in files:
            path = file_info["path"]
            content = file_info["content"]
            ext = file_info["extension"]

            # Skip non-code files for some checks
            is_config = ext in (".yaml", ".yml", ".json", ".toml", ".xml", ".env")
            is_code = ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".rb", ".go", ".rs", ".c", ".cpp", ".cs")

            # 1. Secret detection (all files)
            all_issues.extend(self._scan_secrets(content, path))

            # 2. SQL injection (code files only)
            if is_code:
                all_issues.extend(self._scan_sql_injection(content, path))

            # 3. Insecure practices (code + config files)
            if is_code or is_config:
                all_issues.extend(self._scan_insecure_practices(content, path))

        # 4. LLM deep analysis on a small subset of key files (max 3 files to respect rate limits)
        if llm_client.available:
            code_files = [f for f in files if f["extension"] in (".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".php", ".go")]
            for file_info in code_files[:3]:
                language = project_info.get("primary_language", "unknown")
                llm_issues = await llm_client.analyze_security(
                    file_info["content"], file_info["path"], language
                )
                all_issues.extend(llm_issues)

        # Deduplicate issues by file + line + category
        return self._deduplicate(all_issues)

    def _scan_secrets(self, content: str, file_path: str) -> List[dict]:
        """Scan for hardcoded secrets and credentials."""
        issues = []
        lines = content.split("\n")

        for pattern_info in SECRET_PATTERNS:
            regex = re.compile(pattern_info["pattern"], re.IGNORECASE)
            for line_num, line in enumerate(lines, 1):
                # Skip comments and test/example files
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith("//"):
                    if "example" in stripped.lower() or "placeholder" in stripped.lower():
                        continue

                if regex.search(line):
                    issues.append(self._create_issue(
                        severity=pattern_info["severity"],
                        category="hardcoded_secret",
                        title=f"Hardcoded {pattern_info['name']} detected",
                        description=(
                            f"A potential {pattern_info['name']} was found hardcoded in the source code. "
                            f"Hardcoded secrets can be extracted from version control history and should "
                            f"be stored in environment variables or a secrets manager."
                        ),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                    ))

        return issues

    def _scan_sql_injection(self, content: str, file_path: str) -> List[dict]:
        """Scan for potential SQL injection vulnerabilities."""
        issues = []
        lines = content.split("\n")

        for pattern_info in SQL_INJECTION_PATTERNS:
            regex = re.compile(pattern_info["pattern"], re.IGNORECASE | re.DOTALL)

            # Check multi-line context (3 lines at a time)
            for i in range(len(lines)):
                context = "\n".join(lines[max(0, i):min(len(lines), i + 3)])
                if regex.search(context):
                    issues.append(self._create_issue(
                        severity=pattern_info["severity"],
                        category="sql_injection",
                        title=f"Potential SQL Injection: {pattern_info['name']}",
                        description=(
                            f"User input may be directly concatenated into a SQL query, "
                            f"which can allow an attacker to execute arbitrary SQL commands. "
                            f"Use parameterized queries or an ORM instead."
                        ),
                        file_path=file_path,
                        line_start=i + 1,
                        line_end=min(i + 3, len(lines)),
                        code_snippet=context.strip()[:300],
                    ))

        return issues

    def _scan_insecure_practices(self, content: str, file_path: str) -> List[dict]:
        """Scan for known insecure coding practices."""
        issues = []
        lines = content.split("\n")

        for pattern_info in INSECURE_PATTERNS:
            regex = re.compile(pattern_info["pattern"], re.IGNORECASE)
            for line_num, line in enumerate(lines, 1):
                if regex.search(line):
                    issues.append(self._create_issue(
                        severity=pattern_info["severity"],
                        category=pattern_info.get("category", "insecure_practice"),
                        title=pattern_info["name"],
                        description=pattern_info.get("description", "An insecure coding practice was detected."),
                        file_path=file_path,
                        line_start=line_num,
                        line_end=line_num,
                        code_snippet=line.strip()[:200],
                    ))

        return issues

    def _deduplicate(self, issues: List[dict]) -> List[dict]:
        """Remove duplicate issues based on file + line + category."""
        seen = set()
        unique = []

        for issue in issues:
            key = (
                issue.get("file_path"),
                issue.get("line_start"),
                issue.get("category"),
            )
            if key not in seen:
                seen.add(key)
                unique.append(issue)

        return unique
