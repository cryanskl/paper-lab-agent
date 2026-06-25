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


def test_frontend_api_status_request_normalizes_paths_without_leading_slash(monkeypatch):
    from app import frontend_api

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"items": [], "total": 0}

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "http://api.test/api/v1/papers"
        return FakeResponse()

    monkeypatch.setattr(frontend_api.requests, "request", fake_request)

    status_code, payload = frontend_api.request_json_status("GET", "http://api.test/api/v1/", "papers")

    assert status_code == 200
    assert payload == {"items": [], "total": 0}


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


def test_frontend_api_get_raises_readable_api_error_for_network_error(monkeypatch):
    from app import frontend_api

    monkeypatch.setattr(
        frontend_api,
        "request_json_status",
        lambda *args, **kwargs: (0, {"error": {"code": "request_failed", "message": "timed out"}}),
    )

    try:
        frontend_api.request_json("GET", "http://api.test/api/v1", "/system/status")
    except frontend_api.FrontendApiError as exc:
        assert exc.status_code == 0
        assert str(exc) == "request_failed: timed out"
        assert exc.payload["error"]["code"] == "request_failed"
    else:
        raise AssertionError("expected FrontendApiError")


def test_frontend_api_non_json_error_message_is_bounded():
    from app import frontend_api

    class FakeResponse:
        status_code = 502
        text = "x" * 2000

        def json(self):
            raise ValueError("not json")

    payload = frontend_api.response_payload(FakeResponse())
    message = payload["error"]["message"]

    assert len(message) <= 560
    assert message.startswith("HTTP 502: ")
    assert message.endswith("...")


def test_frontend_api_status_request_promotes_invalid_success_payload(monkeypatch):
    from app import frontend_api

    class FakeResponse:
        status_code = 200
        text = "[1, 2, 3]"

        def json(self):
            return [1, 2, 3]

    monkeypatch.setattr(frontend_api.requests, "request", lambda *args, **kwargs: FakeResponse())

    status_code, payload = frontend_api.request_json_status(
        "POST",
        "http://api.test/api/v1",
        "/crawl/run",
    )

    assert status_code == 599
    assert payload["error"]["code"] == "invalid_response"
    assert "HTTP 200" in payload["error"]["message"]


def test_reaction_review_rows_can_focus_unverified_source_metadata():
    from app import frontend_api

    reactions = [
        {
            "id": 1,
            "reaction": "e + Ar -> e + e + Ar+",
            "verified": 0,
            "confidence": 0.5,
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": "original table value",
            "threshold_ev": 15.76,
            "cross_section_url": "https://nl.lxcat.net/data/set/example",
            "source_section_id": 12,
            "source_section_title": "Table 2",
            "source_section_type": "table",
            "source_section_seq": 4,
            "source_label": "table 4: Table 2",
            "source_excerpt": "e + Ar -> e + e + Ar+ .",
        },
        {
            "id": 2,
            "reaction": "Ar+ + e -> Ar",
            "verified": 1,
            "confidence": 0.9,
            "source_section_title": "Appendix",
        },
    ]

    rows = frontend_api.reaction_review_rows(reactions, only_unverified=True)

    assert rows == [
        {
            "id": 1,
            "verified": False,
            "review_state": "unverified",
            "reaction": "e + Ar -> e + e + Ar+",
            "confidence": 0.5,
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": "original table value",
            "threshold_ev": 15.76,
            "cross_section_url": "https://nl.lxcat.net/data/set/example",
            "source_section": "4 | table | Table 2",
            "source_location": "section 4 · table · Table 2",
            "source_section_id": 12,
            "source_label": "table 4: Table 2",
            "source_excerpt": "e + Ar -> e + e + Ar+ .",
        }
    ]


def test_reaction_review_rows_label_verified_state_and_sparse_source_location():
    from app import frontend_api

    rows = frontend_api.reaction_review_rows(
        [
            {
                "id": 2,
                "reaction": "Ar+ + e -> Ar",
                "verified": 1,
                "source_section_id": 22,
                "source_section_title": "Appendix",
            }
        ]
    )

    assert rows[0]["review_state"] == "verified"
    assert rows[0]["source_location"] == "section 22 · Appendix"


def test_reaction_set_rows_label_export_state_and_review_progress():
    from app import frontend_api

    rows = frontend_api.reaction_set_rows(
        [
            {
                "id": 1,
                "name": "Ar chemistry",
                "status": "verified",
                "reaction_count": 4,
                "verified_count": 4,
                "unverified_count": 0,
                "export_ready": True,
                "verified_by": "engineer_a",
                "verified_at": "2026-06-25T10:00:00",
            },
            {
                "id": 2,
                "name": "O2 chemistry",
                "status": "pending",
                "reaction_count": 5,
                "verified_count": 2,
                "unverified_count": 3,
                "export_ready": False,
            },
            {
                "id": 3,
                "name": "Empty extraction",
                "status": "rejected",
                "reaction_count": 0,
                "verified_count": 0,
                "unverified_count": 0,
                "export_ready": False,
            },
        ]
    )

    assert rows == [
        {
            "id": 1,
            "name": "Ar chemistry",
            "status": "verified",
            "reaction_count": 4,
            "verified_count": 4,
            "unverified_count": 0,
            "export_ready": True,
            "export_state": "ready",
            "review_progress": "4/4 verified",
            "verified_by": "engineer_a",
            "verified_at": "2026-06-25T10:00:00",
        },
        {
            "id": 2,
            "name": "O2 chemistry",
            "status": "pending",
            "reaction_count": 5,
            "verified_count": 2,
            "unverified_count": 3,
            "export_ready": False,
            "export_state": "blocked: 3 unverified",
            "review_progress": "2/5 verified",
            "verified_by": None,
            "verified_at": None,
        },
        {
            "id": 3,
            "name": "Empty extraction",
            "status": "rejected",
            "reaction_count": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "export_ready": False,
            "export_state": "empty",
            "review_progress": "0/0 verified",
            "verified_by": None,
            "verified_at": None,
        },
    ]


def test_rag_source_rows_include_citation_and_location_labels():
    from app import frontend_api

    sources = [
        {
            "document_id": 3,
            "paper_id": 7,
            "paper_title": "Argon plasma chemistry",
            "section_id": 12,
            "section_seq": 4,
            "section_title": "Reaction table",
            "section_type": "table",
            "source_excerpt": "e + Ar -> e + e + Ar+",
            "chunk_id": 19,
            "vector_id": "doc-3-section-12-chunk-19",
            "score": 0.875,
        },
        {
            "document_id": 4,
            "section_id": 20,
            "section_title": "Appendix",
        },
    ]

    rows = frontend_api.rag_source_rows(sources)

    assert rows == [
        {
            "citation": "[paper 7 · doc 3 · section 4 · chunk 19]",
            "source_location": "paper 7 · doc 3 · section 4 · table · Reaction table",
            "document_id": 3,
            "paper_id": 7,
            "paper_title": "Argon plasma chemistry",
            "section_id": 12,
            "section_seq": 4,
            "section_title": "Reaction table",
            "section_type": "table",
            "source_excerpt": "e + Ar -> e + e + Ar+",
            "chunk_id": 19,
            "vector_id": "doc-3-section-12-chunk-19",
            "score": 0.875,
        },
        {
            "citation": "[doc 4 · section 20]",
            "source_location": "doc 4 · section 20 · Appendix",
            "document_id": 4,
            "paper_id": None,
            "paper_title": None,
            "section_id": 20,
            "section_seq": None,
            "section_title": "Appendix",
            "section_type": None,
            "source_excerpt": None,
            "chunk_id": None,
            "vector_id": None,
            "score": None,
        },
    ]
