def test_owner_console_is_available(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "AI Holding — Control Plane" in response.text
    assert "/api/v1/holding/control-plane/owner-view" in response.text
    assert "/api/v1/holding/control-plane/human-actions" in response.text
    assert "Quadros simultâneos por projeto" in response.text
    assert 'id="project-panels"' in response.text
    assert "/api/v1/holding/control-plane/event-feed" in response.text
