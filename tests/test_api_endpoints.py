from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "service" in body


def test_mcp_tools_includes_autocad_and_revit():
    response = client.get("/mcp/tools")
    assert response.status_code == 200
    tools = response.json()["tools"]
    names = {item["name"] for item in tools}
    assert "analyze_revit_3d_vastu_compliance" in names
    assert "analyze_autocad_layout_vastu_compliance" in names
    assert "ingest_vedic_knowledge" in names
    assert "evaluate_room" in names
    assert "resolve_zone" in names


def test_autocad_analyze_endpoint_returns_report():
    payload = {
        "payload": {
            "source": "autocad_layout_2d",
            "true_north_degrees": 0,
            "layout_name": "Ground Floor",
            "entities": [
                {
                    "id": "room-1",
                    "name": "Kitchen",
                    "entity_type": "room",
                    "points": [
                        {"x": 0, "y": 0},
                        {"x": 8, "y": 0},
                        {"x": 8, "y": 6},
                        {"x": 0, "y": 6},
                    ],
                    "metadata": {"room_type": "kitchen"},
                }
            ],
        },
        "context": {"client": "pytest-api"},
    }
    response = client.post("/api/v1/compliance/analyze/autocad", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert "report" in body
    assert body["report"]["summary"]["total_rooms"] == 1
