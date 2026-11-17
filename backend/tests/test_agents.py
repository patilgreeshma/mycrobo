import pytest
from app.agents.security_agent import SecurityAgent
from app.agents.quality_agent import QualityAgent
from app.agents.completeness_agent import CompletenessAgent
from app.agents.dependency_agent import DependencyAgent

@pytest.mark.asyncio
async def test_security_agent_detects_secrets_and_sqli():
    agent = SecurityAgent()
    files = [
        {
            "path": "config.py",
            "extension": ".py",
            "lines": 10,
            "content": 'AWS_SECRET_KEY = "AKIA1234567890ABCDEF"\nDB_PASSWORD = "supersecretpassword123"\n',
        },
        {
            "path": "db.py",
            "extension": ".py",
            "lines": 10,
            "content": 'def get_user(uid):\n    query = f"SELECT * FROM users WHERE id = {uid}"\n    cursor.execute(query)\n',
        }
    ]
    issues = await agent.analyze(files, {})
    assert len(issues) >= 2
    
    categories = [i.get("category", "") for i in issues]
    assert any("secret" in cat or "credential" in cat for cat in categories)
    assert any("sql_injection" in cat for cat in categories)

@pytest.mark.asyncio
async def test_quality_agent_detects_complexity_and_ai_slop():
    agent = QualityAgent()
    # Deeply nested code
    nested_code = """
def process():
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            return True
"""
    files = [
        {
            "path": "complex.py",
            "extension": ".py",
            "lines": 15,
            "content": nested_code,
        },
        {
            "path": "hallucinated.py",
            "extension": ".py",
            "lines": 10,
            "content": '# AI-generated helper\ndef do_nothing():\n    pass # pass\n',
        }
    ]
    issues = await agent.analyze(files, {})
    assert len(issues) >= 1

@pytest.mark.asyncio
async def test_completeness_agent_detects_todos_and_empty_handlers():
    agent = CompletenessAgent()
    files = [
        {
            "path": "auth.py",
            "extension": ".py",
            "lines": 12,
            "content": """
def authenticate(token):
    # TODO: implement JWT validation and expiry check
    try:
        data = decode(token)
    except Exception:
        pass
""",
        }
    ]
    issues = await agent.analyze(files, {})
    assert len(issues) >= 2
    titles = [i.get("title", "").lower() for i in issues]
    assert any("todo" in t or "incomplete" in t for t in titles)
    assert any("exception" in t or "error" in t or "catch" in t for t in titles)

@pytest.mark.asyncio
async def test_dependency_agent_detects_vulnerable_packages():
    agent = DependencyAgent()
    project_info = {
        "dependency_files": [
            {
                "name": "requirements.txt",
                "path": "requirements.txt",
                "type": "python-pip",
                "content": "requests==2.6.0\nlog4j==2.14.0\nflask==0.12\n",
            }
        ]
    }
    issues = await agent.analyze([], project_info)
    assert len(issues) >= 1
    titles = [i.get("title", "").lower() for i in issues]
    assert any("log4j" in t or "outdated" in t or "vulnerable" in t or "requests" in t or "flask" in t for t in titles)
