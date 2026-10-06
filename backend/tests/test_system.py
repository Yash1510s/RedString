"""Unit tests for system diagnostics and demo seed fixture."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_get_system_status() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/system")
        assert resp.status_code == 200
        data = resp.json()
        assert "version" in data
        assert "integrations" in data
        assert len(data["integrations"]) >= 4
        # Assert no secrets in output
        assert "api_key" not in str(data).lower()
        assert "token=" not in str(data).lower()


@pytest.mark.asyncio
async def test_create_demo_investigation_and_verify() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create demo investigation
        resp = await client.post("/api/investigations/demo")
        assert resp.status_code == 201
        data = resp.json()
        inv_id = data["id"]
        assert "Demo Data" in data["target"]
        assert data["findings_count"] >= 8

        # Verify findings exist
        findings_resp = await client.get(f"/api/investigations/{inv_id}/findings")
        assert findings_resp.status_code == 200
        findings = findings_resp.json()
        assert len(findings) >= 8

        # Verify graph exists
        graph_resp = await client.get(f"/api/investigations/{inv_id}/graph")
        assert graph_resp.status_code == 200
        graph = graph_resp.json()
        assert graph["meta"]["nodeCount"] >= 8
        assert graph["meta"]["edgeCount"] >= 5

        # Verify summary exists
        summary_resp = await client.get(f"/api/investigations/{inv_id}/summary")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()
        assert "summary" in summary
        assert len(summary["key_findings"]) >= 2
