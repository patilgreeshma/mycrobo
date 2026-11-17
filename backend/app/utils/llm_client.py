"""
CodeSentinel - LLM Client
Wrapper around Google Gemini API for intelligent code analysis.
Gracefully degrades when no API key is configured.
"""

import json
import logging
from typing import Optional, List

from app.config import settings

logger = logging.getLogger(__name__)

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger.warning("google-generativeai not installed. LLM features disabled.")


class LLMClient:
    """Client for Google Gemini API with graceful fallback."""

    def __init__(self):
        self.model = None
        self.available = False
        self._initialize()

    def _initialize(self):
        """Initialize the Gemini model if API key is available."""
        if not GENAI_AVAILABLE:
            logger.info("LLM client: google-generativeai not installed")
            return

        if not settings.has_gemini_key:
            logger.info("LLM client: No Gemini API key configured")
            return

        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.95,
                    "max_output_tokens": 8192,
                    "response_mime_type": "application/json",
                },
            )
            self.available = True
            logger.info(f"LLM client initialized with model: {settings.GEMINI_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.available = False

    async def analyze_code_issues(
        self,
        code: str,
        file_path: str,
        issues: List[dict],
        language: str = "unknown",
    ) -> List[dict]:
        """
        Enhance detected issues with LLM-powered explanations and fix suggestions.

        Args:
            code: The source code content
            file_path: Path to the file
            issues: List of issues detected by static analysis
            language: Programming language of the file

        Returns:
            Enhanced issues with explanations and suggested fixes
        """
        if not self.available or not issues:
            return issues

        # Build a focused prompt for the issues
        issues_desc = "\n".join(
            f"- [{i.get('severity', 'medium').upper()}] {i.get('title', 'Unknown')} "
            f"at line {i.get('line_start', '?')}: {i.get('description', '')}"
            for i in issues
        )

        prompt = f"""You are a senior code security and quality auditor. Analyze the following issues found in a {language} source file.

FILE: {file_path}
LANGUAGE: {language}

SOURCE CODE:
```{language.lower()}
{code[:6000]}
```

DETECTED ISSUES:
{issues_desc}

For each issue, provide:
1. A clear, context-aware explanation of WHY this is problematic in this specific codebase
2. The potential impact if left unfixed
3. A concrete code suggestion to fix it

Return a JSON array where each element has:
{{
  "index": <issue index starting from 0>,
  "explanation": "<detailed explanation>",
  "suggestion": "<how to fix it>",
  "suggested_code": "<corrected code snippet>",
  "original_code": "<the problematic code snippet>"
}}

Return ONLY the JSON array, no other text."""

        try:
            response = self.model.generate_content(prompt)
            enhanced = json.loads(response.text)

            # Merge LLM enhancements back into issues
            for item in enhanced:
                idx = item.get("index", -1)
                if 0 <= idx < len(issues):
                    issues[idx]["explanation"] = item.get("explanation", "")
                    issues[idx]["suggestion"] = item.get("suggestion", "")
                    issues[idx]["suggested_code"] = item.get("suggested_code", "")
                    issues[idx]["original_code"] = item.get("original_code", "")

            return issues

        except Exception as e:
            logger.warning(f"LLM enhancement failed for {file_path}: {e}")
            return issues

    async def analyze_security(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to perform deep security analysis on code."""
        if not self.available:
            return []

        prompt = f"""You are a cybersecurity expert performing a code audit. Analyze this {language} file for security vulnerabilities.

FILE: {file_path}

```{language.lower()}
{code[:6000]}
```

Look for:
- Hardcoded secrets, API keys, passwords, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Path traversal
- Insecure authentication/authorization
- Insecure deserialization
- Command injection
- Insecure cryptography
- Sensitive data exposure
- Missing security headers

Return a JSON array of found issues. Each issue:
{{
  "severity": "critical|high|medium|low",
  "category": "<category_slug>",
  "title": "<concise title>",
  "description": "<what the issue is>",
  "line_start": <line number or null>,
  "line_end": <line number or null>,
  "code_snippet": "<the problematic code>",
  "explanation": "<why this is dangerous>",
  "suggestion": "<how to fix>",
  "suggested_code": "<fixed code>",
  "original_code": "<original problematic code>"
}}

If no issues found, return an empty array [].
Return ONLY the JSON array."""

        try:
            response = self.model.generate_content(prompt)
            issues = json.loads(response.text)
            for issue in issues:
                issue["agent_type"] = "security"
            return issues
        except Exception as e:
            logger.warning(f"LLM security analysis failed for {file_path}: {e}")
            return []

    async def analyze_quality(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to detect code quality issues and AI slop."""
        if not self.available:
            return []

        prompt = f"""You are a senior software engineer doing a code review. Analyze this {language} file for quality issues.

FILE: {file_path}

```{language.lower()}
{code[:6000]}
```

Look for:
- AI-generated slop: redundant comments that just repeat the code, meaningless variable names, unnecessary wrapper functions, boilerplate that adds no value
- Code duplication within the file
- Overly complex functions (too many nested levels, too long)
- Dead code (unused variables, unreachable code, unused imports)
- Poor error handling patterns
- Anti-patterns specific to {language}
- Inconsistent coding style
- Functions doing too many things (SRP violations)

Return a JSON array of found issues. Each issue:
{{
  "severity": "high|medium|low|info",
  "category": "<category_slug>",
  "title": "<concise title>",
  "description": "<what the issue is>",
  "line_start": <line number or null>,
  "line_end": <line number or null>,
  "code_snippet": "<the problematic code>",
  "explanation": "<why this matters>",
  "suggestion": "<how to improve>",
  "suggested_code": "<improved code>",
  "original_code": "<original code>"
}}

If no issues found, return an empty array [].
Return ONLY the JSON array."""

        try:
            response = self.model.generate_content(prompt)
            issues = json.loads(response.text)
            for issue in issues:
                issue["agent_type"] = "quality"
            return issues
        except Exception as e:
            logger.warning(f"LLM quality analysis failed for {file_path}: {e}")
            return []

    async def analyze_completeness(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to find incomplete implementations and gaps."""
        if not self.available:
            return []

        prompt = f"""You are a tech lead reviewing code for production readiness. Analyze this {language} file for completeness issues.

FILE: {file_path}

```{language.lower()}
{code[:6000]}
```

Look for:
- TODO, FIXME, HACK, XXX comments indicating unfinished work
- Empty or stub function/method bodies (pass, return None, placeholder)
- Missing input validation
- Missing error handling (bare except, missing try/catch around risky operations)
- Incomplete implementations (NotImplementedError, placeholder returns)
- Missing edge case handling
- Missing logging for important operations
- Functions without return type hints or documentation

Return a JSON array of found issues. Each issue:
{{
  "severity": "high|medium|low|info",
  "category": "<category_slug>",
  "title": "<concise title>",
  "description": "<what is missing>",
  "line_start": <line number or null>,
  "line_end": <line number or null>,
  "code_snippet": "<the incomplete code>",
  "explanation": "<why this matters for production>",
  "suggestion": "<what should be implemented>",
  "suggested_code": "<complete implementation>",
  "original_code": "<original incomplete code>"
}}

If no issues found, return an empty array [].
Return ONLY the JSON array."""

        try:
            response = self.model.generate_content(prompt)
            issues = json.loads(response.text)
            for issue in issues:
                issue["agent_type"] = "completeness"
            return issues
        except Exception as e:
            logger.warning(f"LLM completeness analysis failed for {file_path}: {e}")
            return []


# Singleton instance
llm_client = LLMClient()
