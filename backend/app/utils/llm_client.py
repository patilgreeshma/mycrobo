"""
CodeSentinel - LLM Client
Wrapper around Google Gemini API for intelligent code analysis.
Gracefully degrades when no API key is configured or on rate limits/timeouts.
"""

import json
import logging
import asyncio
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
    """Client for Google Gemini API with graceful fallback and timeouts."""

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

    async def _call_gemini(self, prompt: str, timeout: float = 12.0) -> Optional[str]:
        """Safely call Gemini in thread with a strict timeout and error capture."""
        if not self.available or not self.model:
            return None
        try:
            loop = asyncio.get_running_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(None, self.model.generate_content, prompt),
                timeout=timeout,
            )
            return response.text if response else None
        except asyncio.TimeoutError:
            logger.warning(f"Gemini API request timed out after {timeout}s")
            return None
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}")
            return None

    async def analyze_code_issues(
        self,
        code: str,
        file_path: str,
        issues: List[dict],
        language: str = "unknown",
    ) -> List[dict]:
        """
        Enhance detected issues with LLM-powered explanations and fix suggestions.
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
1. A clear, actionable explanation of WHY this is a problem and what could go wrong in production.
2. A specific suggestion for how to fix it.
3. The suggested corrected code that completely fixes the issue.
4. The original problematic code snippet.

Return a JSON array where each element matches the corresponding issue in order:
[
  {{
    "index": 0,
    "explanation": "Detailed explanation of the root cause and impact...",
    "suggestion": "Specific instructions to fix...",
    "suggested_code": "The corrected code...",
    "original_code": "The original code being replaced..."
  }}
]

Return ONLY the JSON array, no other text."""

        raw_json = await self._call_gemini(prompt, timeout=12.0)
        if not raw_json:
            return issues

        try:
            enhancements = json.loads(raw_json)
            for item in enhancements:
                idx = item.get("index", -1)
                if 0 <= idx < len(issues):
                    issues[idx]["explanation"] = item.get("explanation", issues[idx].get("explanation"))
                    issues[idx]["suggestion"] = item.get("suggestion", issues[idx].get("suggestion"))
                    issues[idx]["suggested_code"] = item.get("suggested_code", issues[idx].get("suggested_code"))
                    issues[idx]["original_code"] = item.get("original_code", issues[idx].get("original_code"))
            return issues
        except Exception as e:
            logger.warning(f"Failed to parse LLM enhancement JSON for {file_path}: {e}")
            return issues

    async def analyze_security(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to perform deep security analysis on code."""
        if not self.available:
            return []

        prompt = f"""You are a cybersecurity expert performing a code audit. Analyze this {language} file for security vulnerabilities.

FILE: {file_path}

```{language.lower()}
{code[:5000]}
```

Look for:
- Hardcoded secrets, API keys, passwords, tokens
- SQL injection vulnerabilities
- XSS vulnerabilities
- Insecure authentication/authorization
- Command injection

Return a JSON array of found issues:
[
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
]
If none found, return []. Return ONLY valid JSON array."""

        raw_json = await self._call_gemini(prompt, timeout=10.0)
        if not raw_json:
            return []

        try:
            issues = json.loads(raw_json)
            for issue in issues:
                issue["agent_type"] = "security"
            return issues
        except Exception as e:
            logger.warning(f"Failed to parse LLM security output for {file_path}: {e}")
            return []

    async def analyze_quality(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to detect code quality issues and AI slop."""
        if not self.available:
            return []

        prompt = f"""You are a senior software engineer doing a code review. Analyze this {language} file for quality issues.

FILE: {file_path}

```{language.lower()}
{code[:5000]}
```

Look for AI slop (redundant wrappers, meaningless boilerplate), duplicate logic, dead code, excessive complexity.

Return a JSON array:
[
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
]
If none found, return []. Return ONLY valid JSON array."""

        raw_json = await self._call_gemini(prompt, timeout=10.0)
        if not raw_json:
            return []

        try:
            issues = json.loads(raw_json)
            for issue in issues:
                issue["agent_type"] = "quality"
            return issues
        except Exception as e:
            logger.warning(f"Failed to parse LLM quality output for {file_path}: {e}")
            return []

    async def analyze_completeness(self, code: str, file_path: str, language: str) -> List[dict]:
        """Use LLM to find incomplete implementations and gaps."""
        if not self.available:
            return []

        prompt = f"""You are a tech lead reviewing code for production readiness. Analyze this {language} file for completeness issues.

FILE: {file_path}

```{language.lower()}
{code[:5000]}
```

Look for unfinished TODOs, empty catch blocks, missing validations, incomplete stubs.

Return a JSON array:
[
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
]
If none found, return []. Return ONLY valid JSON array."""

        raw_json = await self._call_gemini(prompt, timeout=10.0)
        if not raw_json:
            return []

        try:
            issues = json.loads(raw_json)
            for issue in issues:
                issue["agent_type"] = "completeness"
            return issues
        except Exception as e:
            logger.warning(f"Failed to parse LLM completeness output for {file_path}: {e}")
            return []


# Singleton
llm_client = LLMClient()
