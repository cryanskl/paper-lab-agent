def test_frontend_api_status_request_preserves_non_json_error(monkeypatch):
    from app import frontend_api

    class FakeResponse:
        status_code = 502
        text = "<html>bad gateway</html>"

        def json(self):
            raise ValueError("not json")

    def fake_request(method, url, **kwargs):
        assert method == "POST"
        assert url == "http://api.test/api/v1/crawl/run"
        assert kwargs["timeout"] == 60
        return FakeResponse()

    monkeypatch.setattr(frontend_api.requests, "request", fake_request)

    status_code, payload = frontend_api.request_json_status(
        "POST",
        "http://api.test/api/v1",
        "/crawl/run",
        json={"period": "manual"},
        timeout=60,
    )

    assert status_code == 502
    assert payload == {
        "error": {
            "code": "http_error",
            "message": "HTTP 502: <html>bad gateway</html>",
        }
    }


def test_frontend_api_get_raises_readable_api_error_for_json_error(monkeypatch):
    from app import frontend_api

    class FakeResponse:
        status_code = 409
        text = ""

        def json(self):
            return {"error": {"code": "reaction_set_unverified", "message": "reaction set has unverified reactions"}}

    monkeypatch.setattr(frontend_api.requests, "request", lambda *args, **kwargs: FakeResponse())

    try:
        frontend_api.request_json("GET", "http://api.test/api/v1", "/reaction-sets/1")
    except frontend_api.FrontendApiError as exc:
        assert exc.status_code == 409
        assert str(exc) == "reaction_set_unverified: reaction set has unverified reactions"
        assert exc.payload["error"]["code"] == "reaction_set_unverified"
    else:
        raise AssertionError("expected FrontendApiError")


def test_frontend_api_status_request_converts_network_error_to_payload(monkeypatch):
    from app import frontend_api

    def fake_request(*args, **kwargs):
        raise frontend_api.requests.Timeout("timed out")

    monkeypatch.setattr(frontend_api.requests, "request", fake_request)

    status_code, payload = frontend_api.request_json_status(
        "GET",
        "http://api.test/api/v1",
        "/system/status",
        timeout=1,
    )

    assert status_code == 0
    assert payload == {
        "error": {
            "code": "request_failed",
            "message": "timed out",
        }
    }
