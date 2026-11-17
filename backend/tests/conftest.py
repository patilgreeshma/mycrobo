import pytest
from app.utils.llm_client import llm_client
from app.config import settings

@pytest.fixture(autouse=True)
def disable_external_llm_for_tests(monkeypatch):
    """Disable live external LLM API calls during test suite execution."""
    monkeypatch.setattr(llm_client, "available", False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
