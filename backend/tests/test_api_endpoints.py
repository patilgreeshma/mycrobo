import io
import asyncio
import zipfile
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.models.database import init_db, close_db

@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    yield
    await close_db()

def create_sample_zip():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "config.py",
            'API_KEY = "sk-live-1234567890abcdef12345678"\nDEBUG = True\n'
        )
        zf.writestr(
            "app.py",
            '# TODO: Add authentication\ndef query(user):\n    return f"SELECT * FROM items WHERE user = {user}"\n'
        )
        zf.writestr(
            "requirements.txt",
            "requests==2.6.0\nlog4j==2.14.0\n"
        )
    buf.seek(0)
    return buf

@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "version" in data

@pytest.mark.asyncio
async def test_scans_list_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/scans")
        assert res.status_code == 200
        data = res.json()
        assert "scans" in data
        assert "total" in data

@pytest.mark.asyncio
async def test_zip_upload_and_scan_flow():
    zip_buf = create_sample_zip()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Upload scan
        files = {"file": ("test_project.zip", zip_buf, "application/zip")}
        data = {"project_name": "Test Project"}
        res = await client.post("/api/scans/upload", files=files, data=data)
        assert res.status_code == 200
        scan_id = res.json()["scan_id"]
        assert scan_id is not None

        # 2. Poll until complete (or max 10 iterations)
        completed = False
        for _ in range(15):
            await asyncio.sleep(0.3)
            scan_res = await client.get(f"/api/scans/{scan_id}")
            assert scan_res.status_code == 200
            scan_data = scan_res.json()
            if scan_data["scan"]["status"] == "complete":
                completed = True
                break

        assert completed, "Scan did not reach 'complete' status in time"

        # 3. Verify scan findings
        scan_details = scan_data["scan"]
        issues = scan_data["issues"]
        assert scan_details["total_issues"] > 0
        assert len(issues) > 0
        assert scan_details["health_score"] < 100.0

        # 4. Verify report endpoints
        # Markdown export
        md_res = await client.get(f"/api/scans/{scan_id}/report?format=markdown")
        assert md_res.status_code == 200
        md_data = md_res.json()
        assert "content" in md_data
        assert "CodeSentinel Audit Report" in md_data["content"]

        # JSON export
        json_res = await client.get(f"/api/scans/{scan_id}/report?format=json")
        assert json_res.status_code == 200
        json_data = json_res.json()
        assert "metadata" in json_data
        assert "issues" in json_data
