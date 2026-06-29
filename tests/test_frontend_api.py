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


def test_frontend_api_status_request_strips_base_url_whitespace(monkeypatch):
    from app import frontend_api

    class FakeResponse:
        status_code = 200
        text = "{}"

        def json(self):
            return {"ok": True}

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url == "http://api.test/api/v1/system/status"
        return FakeResponse()

    monkeypatch.setattr(frontend_api.requests, "request", fake_request)

    status_code, payload = frontend_api.request_json_status(
        "GET",
        "  http://api.test/api/v1/  ",
        "system/status",
    )

    assert status_code == 200
    assert payload == {"ok": True}


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


def test_release_readiness_display_state_surfaces_only_blocking_config_warnings():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(
        {
            "ready": False,
            "demo_data_missing": [],
            "failed_workflows": [],
            "config_warning_codes": ["missing_llm_api_key", "unsupported_vector_db_backend"],
            "storage_errors": [],
        }
    )

    assert state["ready"] is False
    assert state["blockers"] == ["config_warning_codes:unsupported_vector_db_backend"]
    assert {
        "label": "config warnings:",
        "items": ["config_warning_codes:unsupported_vector_db_backend"],
    } in state["groups"]
    assert "config_warning_codes:missing_llm_api_key" not in state["blockers"]


def test_release_readiness_display_state_blocks_malformed_config_warning_codes():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(
        {
            "ready": True,
            "demo_data_missing": [],
            "failed_workflows": [],
            "config_warning_codes": "unsupported_vector_db_backend",
            "storage_errors": [],
        }
    )

    assert state["ready"] is False
    assert state["blockers"] == ["config_warning_codes:invalid"]
    assert {
        "label": "config warnings:",
        "items": ["config_warning_codes:invalid"],
    } in state["groups"]


def test_release_readiness_display_state_blocks_malformed_demo_data_missing():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(
        {
            "ready": True,
            "demo_data_missing": "documents>=1",
            "failed_workflows": [],
            "config_warning_codes": [],
            "storage_errors": [],
        }
    )

    assert state["ready"] is False
    assert state["blockers"] == ["invalid"]
    assert {
        "label": "demo data missing:",
        "items": ["invalid"],
    } in state["groups"]


def test_release_readiness_display_state_rejects_inconsistent_ready_payload():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(
        {
            "ready": True,
            "demo_data_missing": ["documents>=1"],
            "failed_workflows": [],
            "config_warning_codes": [],
            "storage_errors": [],
        }
    )

    assert state["ready"] is False
    assert state["blockers"] == ["documents>=1"]
    assert {
        "label": "demo data missing:",
        "items": ["documents>=1"],
    } in state["groups"]


def test_release_readiness_display_state_surfaces_ready_false_without_details():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(
        {
            "ready": False,
            "demo_data_missing": [],
            "failed_workflows": [],
            "config_warning_codes": [],
            "storage_errors": [],
        }
    )

    assert state["ready"] is False
    assert state["blockers"] == ["ready=false"]
    assert {
        "label": "release state:",
        "items": ["ready=false"],
    } in state["groups"]


def test_release_readiness_display_state_blocks_malformed_readiness_object():
    from app import frontend_api

    state = frontend_api.release_readiness_display_state(["ready"])

    assert state["ready"] is False
    assert state["blockers"] == ["release_readiness:invalid"]
    assert {
        "label": "release state:",
        "items": ["release_readiness:invalid"],
    } in state["groups"]


def test_demo_data_display_state_blocks_malformed_demo_data_object():
    from app import frontend_api

    state = frontend_api.demo_data_display_state(["ready"])

    assert state["ready"] is False
    assert state["missing"] == ["demo_data:invalid"]


def test_health_display_state_blocks_malformed_health_payloads():
    from app import frontend_api

    assert frontend_api.health_display_state(
        {"service": "paper-lab-agent", "status": "ok"}
    ) == {
        "caption": "paper-lab-agent · ok",
        "warning": None,
    }

    assert frontend_api.health_display_state({"service": "", "status": ["ok"]}) == {
        "caption": "service:invalid · status:invalid",
        "warning": "health: invalid",
    }
    assert frontend_api.health_display_state(["health"]) == {
        "caption": "service:invalid · status:invalid",
        "warning": "health: invalid",
    }


def test_system_count_metric_rows_blocks_malformed_counts_objects():
    from app import frontend_api

    rows = frontend_api.system_count_metric_rows(["counts"])

    assert rows == [{"label": "系统计数", "value": "invalid", "warning": "counts: invalid"}]

    nested_rows = frontend_api.system_count_metric_rows({"journals": False, "papers": 2, "documents": 1})

    assert nested_rows == [
        {"label": "期刊", "value": "invalid", "warning": "counts.journals: invalid"},
        {"label": "论文", "value": 2, "warning": None},
        {"label": "文档", "value": 1, "warning": None},
    ]


def test_runtime_status_rows_blocks_malformed_runtime_objects():
    from app import frontend_api

    rows = frontend_api.runtime_status_rows(["runtime"])

    assert rows == [{"kind": "warning", "text": "runtime: invalid"}]

    nested_rows = frontend_api.runtime_status_rows(
        {
            "api_prefix": "/api/v1",
            "version": "0.1.0",
            "scheduler_enabled": False,
            "scheduler_jobs": ["bad"],
        }
    )

    assert {"kind": "caption", "text": "API: /api/v1"} in nested_rows
    assert {"kind": "warning", "text": "scheduler_jobs: invalid"} in nested_rows


def test_runtime_status_rows_blocks_malformed_scheduler_enabled():
    from app import frontend_api

    rows = frontend_api.runtime_status_rows(
        {
            "api_prefix": "/api/v1",
            "version": "0.1.0",
            "scheduler_enabled": "yes",
            "scheduler_jobs": [],
        }
    )

    assert {"kind": "warning", "text": "scheduler_enabled: invalid"} in rows
    assert {"kind": "caption", "text": "scheduler_enabled: True"} not in rows


def test_runtime_status_rows_blocks_malformed_api_prefix():
    from app import frontend_api

    rows = frontend_api.runtime_status_rows(
        {
            "api_prefix": ["api"],
            "version": "0.1.0",
            "scheduler_enabled": False,
            "scheduler_jobs": [],
        }
    )

    assert {"kind": "warning", "text": "api_prefix: invalid"} in rows
    assert {"kind": "caption", "text": "API: ['api']"} not in rows


def test_runtime_status_rows_blocks_malformed_version():
    from app import frontend_api

    rows = frontend_api.runtime_status_rows(
        {
            "api_prefix": "/api/v1",
            "version": ["0.1.0"],
            "scheduler_enabled": False,
            "scheduler_jobs": [],
        }
    )

    assert {"kind": "warning", "text": "version: invalid"} in rows
    assert {"kind": "caption", "text": "version: ['0.1.0']"} not in rows


def test_runtime_status_rows_blocks_malformed_scheduler_job_fields():
    from app import frontend_api

    rows = frontend_api.runtime_status_rows(
        {
            "api_prefix": "/api/v1",
            "version": "0.1.0",
            "scheduler_enabled": False,
            "scheduler_jobs": [
                {
                    "period": ["daily"],
                    "id": "crawl-daily",
                    "schedule": "",
                    "timezone": "UTC",
                }
            ],
        }
    )

    assert {"kind": "warning", "text": "scheduler_jobs: invalid"} in rows
    assert {"kind": "caption", "text": "- ['daily'] · crawl-daily ·  UTC"} not in rows


def test_database_path_status_row_blocks_malformed_database_path():
    from app import frontend_api

    assert frontend_api.database_path_status_row("/tmp/plasma.db") == {
        "kind": "caption",
        "text": "DB: /tmp/plasma.db",
    }

    assert frontend_api.database_path_status_row("") == {
        "kind": "warning",
        "text": "database_path: invalid",
    }
    assert frontend_api.database_path_status_row(False) == {
        "kind": "warning",
        "text": "database_path: invalid",
    }


def test_storage_health_caption_rows_include_parent_dirs_and_vector_json_state():
    from app import frontend_api

    rows = frontend_api.storage_health_caption_rows(
        {
            "data_dir": {"path": "data", "exists": True, "writable": True},
            "database": {"path": "data/plasma.db", "exists": True, "writable": True},
            "database_parent": {"path": "data", "exists": True, "writable": True},
            "vector_db_parent": {"path": "data", "exists": True, "writable": True},
            "vector_db": {
                "path": "data/vector-index.json",
                "exists": True,
                "writable": True,
                "valid_json": False,
                "error": "invalid json",
            },
        }
    )

    assert rows == [
        {"kind": "caption", "text": "data_dir: exists · writable · data"},
        {"kind": "caption", "text": "pdf_dir: missing · not writable · -"},
        {"kind": "caption", "text": "tei_dir: missing · not writable · -"},
        {"kind": "caption", "text": "translation_dir: missing · not writable · -"},
        {"kind": "caption", "text": "export_dir: missing · not writable · -"},
        {"kind": "caption", "text": "database: exists · writable · data/plasma.db"},
        {"kind": "caption", "text": "database_parent: exists · writable · data"},
        {"kind": "caption", "text": "vector_db_parent: exists · writable · data"},
        {"kind": "caption", "text": "vector_db: exists · writable · data/vector-index.json"},
        {"kind": "caption", "text": "vector_db valid_json: invalid_json"},
        {"kind": "warning", "text": "vector_db error: invalid json"},
    ]


def test_storage_health_caption_rows_blocks_malformed_storage_health_object():
    from app import frontend_api

    rows = frontend_api.storage_health_caption_rows(["storage"])

    assert rows == [{"kind": "warning", "text": "storage_health: invalid"}]


def test_storage_health_caption_rows_blocks_malformed_storage_health_entries():
    from app import frontend_api

    rows = frontend_api.storage_health_caption_rows(
        {
            "data_dir": {"path": "data", "exists": True, "writable": True},
            "database": "bad",
        }
    )

    assert {"kind": "warning", "text": "database: invalid"} in rows
    assert {"kind": "caption", "text": "data_dir: exists · writable · data"} in rows


def test_storage_health_caption_rows_blocks_malformed_storage_health_fields():
    from app import frontend_api

    rows = frontend_api.storage_health_caption_rows(
        {
            "data_dir": {"path": ["data"], "exists": "yes", "writable": True},
        }
    )

    assert {"kind": "warning", "text": "data_dir: invalid"} in rows
    assert {"kind": "caption", "text": "data_dir: exists · writable · ['data']"} not in rows


def test_external_capabilities_display_state_blocks_malformed_objects():
    from app import frontend_api

    state = frontend_api.external_capabilities_display_state(["external"])

    assert state == {
        "capabilities": {},
        "grobid": {},
        "warnings": ["external_capabilities:invalid"],
    }

    nested_state = frontend_api.external_capabilities_display_state({"grobid": ["bad"]})

    assert nested_state == {
        "capabilities": {"grobid": ["bad"]},
        "grobid": {},
        "warnings": ["grobid:invalid"],
    }


def test_external_capabilities_display_state_blocks_malformed_capability_fields():
    from app import frontend_api

    state = frontend_api.external_capabilities_display_state(
        {
            "openalex_mailto": "yes",
            "unpaywall_email": False,
            "translation_adapter": ["local-echo"],
            "grobid": {"available": None},
        }
    )

    assert "external_capabilities:invalid" in state["warnings"]
    assert state["capabilities"]["openalex_mailto"] is False
    assert state["capabilities"]["unpaywall_email"] is False
    assert state["capabilities"]["translation_adapter"] == ""


def test_external_capabilities_display_state_blocks_malformed_grobid_fields():
    from app import frontend_api

    state = frontend_api.external_capabilities_display_state(
        {
            "grobid": {
                "url": ["http://127.0.0.1:8070"],
                "available": "yes",
                "status_code": "200",
                "error": ["bad"],
            }
        }
    )

    assert "grobid:invalid" in state["warnings"]
    assert state["grobid"] == {}


def test_status_count_rows_blocks_malformed_status_counts_objects():
    from app import frontend_api

    rows = frontend_api.status_count_rows(["counts"])

    assert rows == [{"workflow": "status_counts", "status": "invalid", "count": 1}]

    nested_rows = frontend_api.status_count_rows({"document_parse": ["bad"]})

    assert nested_rows == [{"workflow": "document_parse", "status": "invalid", "count": 1}]


def test_status_count_rows_blocks_malformed_status_count_values():
    from app import frontend_api

    rows = frontend_api.status_count_rows({"crawl_jobs": {"success": 2, "failed": True}})

    assert {"workflow": "crawl_jobs", "status": "success", "count": 2} in rows
    assert {"workflow": "crawl_jobs", "status": "invalid", "count": 1} in rows
    assert {"workflow": "crawl_jobs", "status": "failed", "count": True} not in rows


def test_config_warning_rows_blocks_malformed_config_warning_objects():
    from app import frontend_api

    rows = frontend_api.config_warning_rows("missing_llm_api_key")

    assert rows == [{"capability": "config_warnings", "message": "invalid"}]

    nested_rows = frontend_api.config_warning_rows([False])

    assert nested_rows == [{"capability": "config_warnings", "message": "invalid"}]


def test_config_warning_rows_blocks_malformed_config_warning_fields():
    from app import frontend_api

    rows = frontend_api.config_warning_rows(
        [{"capability": ["llm_translation"], "message": True}]
    )

    assert rows == [{"capability": "config_warnings", "message": "invalid"}]


def test_crawl_job_option_label_summarizes_job_status():
    from app import frontend_api

    label = frontend_api.crawl_job_option_label({"id": 12, "journal_id": 3, "status": "success"})

    assert label == "#12 · journal 3 · success"


def test_crawl_job_option_label_uses_fallbacks_for_sparse_jobs():
    from app import frontend_api

    label = frontend_api.crawl_job_option_label({"job_id": 9})

    assert label == "#9 · journal - · unknown"


def test_crawl_job_items_skip_malformed_items():
    from app import frontend_api

    valid_job = {"id": 9, "status": "success"}

    assert frontend_api.crawl_job_items(
        [
            "bad-job",
            {"status": "missing id"},
            {"id": "9", "status": "string id"},
            {"id": False, "status": "bool id"},
            valid_job,
        ]
    ) == [valid_job]


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
            "export_blocker": "unverified reaction",
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


def test_reaction_review_rows_mark_export_blockers():
    from app import frontend_api

    rows = frontend_api.reaction_review_rows(
        [
            {"id": 1, "reaction": "e + Ar -> e + e + Ar+", "verified": 0},
            {"id": 2, "reaction": "Ar+ + e -> Ar", "verified": 1},
        ]
    )

    assert rows[0]["export_blocker"] == "unverified reaction"
    assert rows[1]["export_blocker"] is None


def test_reaction_review_rows_skip_malformed_reactions():
    from app import frontend_api

    rows = frontend_api.reaction_review_rows(
        [
            "bad-reaction",
            {"id": 1, "reaction": "e + Ar -> e + e + Ar+", "verified": 0},
        ]
    )

    assert len(rows) == 1
    assert rows[0]["id"] == 1
    assert rows[0]["review_state"] == "unverified"


def test_reaction_display_state_summarizes_review_card_metadata():
    from app import frontend_api

    state = frontend_api.reaction_display_state(
        {
            "reaction": "e + Ar -> 2e + Ar+",
            "verified": 0,
            "confidence": 0.72,
            "source_section_id": 12,
            "source_section_title": "Table 2",
            "source_section_type": "table",
            "source_section_seq": 4,
            "source_label": "table 4: Table 2",
            "source_excerpt": "Measured ionization cross section.",
            "reactants": '["e", "Ar"]',
            "products": '["e", "e", "Ar+"]',
            "reference": "Smith 2024",
        }
    )

    assert state == {
        "reaction": "e + Ar -> 2e + Ar+",
        "source_excerpt": "Measured ionization cross section.",
        "source_summary": (
            "verified: False · confidence: 0.72 · source_section_id: 12 · "
            "source_section_title: Table 2 · source_section_type: table · "
            "source_section_seq: 4 · source_label: table 4: Table 2"
        ),
        "species_summary": 'reactants: ["e", "Ar"] · products: ["e", "e", "Ar+"] · reference: Smith 2024',
    }


def test_reaction_display_state_uses_dash_fallbacks_for_sparse_metadata():
    from app import frontend_api

    state = frontend_api.reaction_display_state({"reaction": "Ar+ + e -> Ar"})

    assert state == {
        "reaction": "Ar+ + e -> Ar",
        "source_excerpt": None,
        "source_summary": (
            "verified: False · confidence: None · source_section_id: None · "
            "source_section_title: - · source_section_type: - · "
            "source_section_seq: - · source_label: -"
        ),
        "species_summary": "reactants: - · products: - · reference: -",
    }


def test_reaction_set_rows_label_export_state_and_review_progress():
    from app import frontend_api

    rows = frontend_api.reaction_set_rows(
        [
            {
                "id": 1,
                "document_id": 7,
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
                "document_id": 7,
                "name": "O2 chemistry",
                "status": "pending",
                "reaction_count": 5,
                "verified_count": 2,
                "unverified_count": 3,
                "export_ready": False,
            },
            {
                "id": 3,
                "document_id": 8,
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
            "document_id": 7,
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
            "document_id": 7,
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
            "document_id": 8,
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


def test_reaction_set_rows_handle_malformed_counts_and_export_state():
    from app import frontend_api

    rows = frontend_api.reaction_set_rows(
        [
            {
                "id": 4,
                "document_id": 9,
                "name": "Malformed extraction",
                "status": "pending",
                "reaction_count": ["4"],
                "verified_count": "2",
                "unverified_count": ["2"],
                "export_ready": "yes",
            }
        ]
    )

    assert rows == [
        {
            "id": 4,
            "document_id": 9,
            "name": "Malformed extraction",
            "status": "pending",
            "reaction_count": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "export_ready": False,
            "export_state": "empty",
            "review_progress": "0/0 verified",
            "verified_by": None,
            "verified_at": None,
        }
    ]


def test_reaction_set_rows_handle_non_object_items():
    from app import frontend_api

    rows = frontend_api.reaction_set_rows(["bad-reaction-set"])

    assert rows == [
        {
            "id": None,
            "document_id": None,
            "name": "Reaction set",
            "status": "invalid",
            "reaction_count": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "export_ready": False,
            "export_state": "empty",
            "review_progress": "0/0 verified",
            "verified_by": None,
            "verified_at": None,
        }
    ]


def test_reaction_set_option_label_summarizes_review_and_export_state():
    from app import frontend_api

    label = frontend_api.reaction_set_option_label(
        {
            "id": 3,
            "document_id": 7,
            "name": "Ar chemistry",
            "status": "pending",
            "export_ready": False,
            "unverified_count": 2,
        }
    )

    assert label == "#3 · doc 7 · pending · export_ready False · 未复核 2 · Ar chemistry"


def test_reaction_set_option_label_uses_fallbacks_for_sparse_items():
    from app import frontend_api

    label = frontend_api.reaction_set_option_label({"id": 8})

    assert label == "#8 · unknown · export_ready False · 未复核 0 · Reaction set"


def test_reaction_set_options_skip_malformed_items():
    from app import frontend_api

    valid_reaction_set = {"id": 3, "status": "pending"}

    assert frontend_api.reaction_set_options(["bad-reaction-set", valid_reaction_set, None]) == [valid_reaction_set]


def test_reaction_set_options_skip_items_without_valid_id():
    from app import frontend_api

    valid_reaction_set = {"id": 3, "status": "pending"}

    assert frontend_api.reaction_set_options(
        [
            {"status": "missing-id"},
            {"id": "3", "status": "string-id"},
            {"id": True, "status": "bool-id"},
            valid_reaction_set,
        ]
    ) == [valid_reaction_set]


def test_reaction_set_option_label_handles_malformed_items():
    from app import frontend_api

    label = frontend_api.reaction_set_option_label(
        {
            "document_id": ["7"],
            "status": ["pending"],
            "export_ready": "yes",
            "unverified_count": ["2"],
            "name": ["Ar chemistry"],
        }
    )

    assert label == "#- · unknown · export_ready False · 未复核 0 · Reaction set"


def test_reaction_set_option_label_handles_non_object_item():
    from app import frontend_api

    assert frontend_api.reaction_set_option_label("bad-reaction-set") == (
        "#- · unknown · export_ready False · 未复核 0 · Reaction set"
    )


def test_reaction_review_payload_normalizes_edit_form_values():
    from app import frontend_api

    payload = frontend_api.reaction_review_payload(
        verified=True,
        reaction_type=" ionization ",
        rate_type=" cross_section ",
        rate_value="  original table value  ",
        include_threshold_ev=True,
        threshold_ev=15.76,
        cross_section_url=" https://nl.lxcat.net/data/set/example ",
        verified_by=" engineer_a ",
    )

    assert payload == {
        "verified": True,
        "reaction_type": "ionization",
        "rate_type": "cross_section",
        "rate_value": "original table value",
        "threshold_ev": 15.76,
        "cross_section_url": "https://nl.lxcat.net/data/set/example",
        "verified_by": "engineer_a",
    }


def test_reaction_review_payload_clears_disabled_and_blank_fields():
    from app import frontend_api

    payload = frontend_api.reaction_review_payload(
        verified=False,
        reaction_type="",
        rate_type="",
        rate_value="   ",
        include_threshold_ev=False,
        threshold_ev=15.76,
        cross_section_url="",
        verified_by=" streamlit ",
    )

    assert payload == {
        "verified": False,
        "reaction_type": None,
        "rate_type": None,
        "rate_value": None,
        "threshold_ev": None,
        "cross_section_url": None,
        "verified_by": "streamlit",
    }


def test_reaction_review_form_state_normalizes_unknown_types_and_zero_threshold():
    from app import frontend_api

    state = frontend_api.reaction_review_form_state(
        {
            "id": 11,
            "reaction_type": "unknown",
            "rate_type": "unknown",
            "threshold_ev": 0,
            "rate_value": "original value",
            "cross_section_url": "https://example.test/cross-section",
            "verified": True,
        }
    )

    assert state == {
        "reaction_type_options": ["", "elastic", "excitation", "ionization", "attachment", "recombination"],
        "rate_type_options": ["", "cross_section", "arrhenius", "constant"],
        "reaction_type_value": "",
        "reaction_type_index": 0,
        "rate_type_value": "",
        "rate_type_index": 0,
        "include_threshold_ev": True,
        "threshold_ev_value": 0.0,
        "rate_value": "original value",
        "cross_section_url": "https://example.test/cross-section",
        "verified": True,
        "verified_by": "streamlit",
    }


def test_reaction_review_form_state_preserves_known_type_indexes_and_blank_text():
    from app import frontend_api

    state = frontend_api.reaction_review_form_state(
        {
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "rate_value": None,
            "cross_section_url": None,
            "verified": False,
        }
    )

    assert state["reaction_type_index"] == 3
    assert state["rate_type_index"] == 1
    assert state["include_threshold_ev"] is False
    assert state["threshold_ev_value"] == 0.0
    assert state["rate_value"] == ""
    assert state["cross_section_url"] == ""
    assert state["verified"] is False
    assert state["verified_by"] == "streamlit"


def test_reaction_review_form_state_ignores_malformed_threshold():
    from app import frontend_api

    state = frontend_api.reaction_review_form_state(
        {
            "reaction_type": "ionization",
            "rate_type": "cross_section",
            "threshold_ev": "not-a-number",
            "verified": False,
        }
    )

    assert state["include_threshold_ev"] is False
    assert state["threshold_ev_value"] == 0.0


def test_reaction_export_rows_summarize_download_and_audit_metadata():
    from app import frontend_api

    rows = frontend_api.reaction_export_rows(
        {
            "reaction_set_id": 3,
            "format": "bolsig",
            "output_path": "/tmp/exports/reaction-set-3.bolsig.txt",
            "mime_type": "text/plain",
            "reaction_count": 4,
            "audit_entry_count": 4,
        }
    )

    assert rows == [
        {"field": "reaction_set_id", "value": 3},
        {"field": "format", "value": "bolsig"},
        {"field": "output_path", "value": "/tmp/exports/reaction-set-3.bolsig.txt"},
        {"field": "mime_type", "value": "text/plain"},
        {"field": "reaction_count", "value": 4},
        {"field": "audit_entry_count", "value": 4},
        {"field": "download_label", "value": "bolsig · 4 reactions · 4 audit entries"},
    ]


def test_reaction_export_rows_handle_malformed_counts():
    from app import frontend_api

    rows = frontend_api.reaction_export_rows(
        {
            "reaction_set_id": 3,
            "format": "json",
            "output_path": "/tmp/exports/reaction-set-3.json",
            "mime_type": "application/json",
            "reaction_count": ["4"],
            "audit_entry_count": "4",
        }
    )

    assert rows == [
        {"field": "reaction_set_id", "value": 3},
        {"field": "format", "value": "json"},
        {"field": "output_path", "value": "/tmp/exports/reaction-set-3.json"},
        {"field": "mime_type", "value": "application/json"},
        {"field": "reaction_count", "value": 0},
        {"field": "audit_entry_count", "value": 0},
        {"field": "download_label", "value": "json · 0 reactions · 0 audit entries"},
    ]


def test_reaction_export_success_state_blocks_malformed_success_payloads():
    from app import frontend_api

    assert frontend_api.reaction_export_success_state(
        {"output_path": "/tmp/exports/reaction-set-3.json"}
    ) == {
        "message": "/tmp/exports/reaction-set-3.json",
        "warning": None,
    }
    assert frontend_api.reaction_export_success_state({"output_path": ""}) == {
        "message": "export path unavailable",
        "warning": "reaction export response: invalid",
    }
    assert frontend_api.reaction_export_success_state(["export"]) == {
        "message": "export path unavailable",
        "warning": "reaction export response: invalid",
    }


def test_reaction_export_download_reads_text_file_for_streamlit_button(tmp_path):
    from app import frontend_api

    export_path = tmp_path / "reaction-set-3.txt"
    export_path.write_text("e + Ar -> e + e + Ar+\n", encoding="utf-8")

    download = frontend_api.reaction_export_download(
        {
            "format": "txt",
            "output_path": str(export_path),
            "mime_type": "text/plain",
        }
    )

    assert download == {
        "label": "下载导出文件",
        "data": "e + Ar -> e + e + Ar+\n",
        "file_name": "reaction-set-3.txt",
        "mime": "text/plain",
        "path": str(export_path),
    }


def test_reaction_export_download_reads_binary_file_for_non_text_mime(tmp_path):
    from app import frontend_api

    export_path = tmp_path / "reaction-set-3.bin"
    export_path.write_bytes(b"\x00\x01")

    download = frontend_api.reaction_export_download(
        {
            "output_path": str(export_path),
            "mime_type": "application/octet-stream",
        }
    )

    assert download == {
        "label": "下载导出文件",
        "data": b"\x00\x01",
        "file_name": "reaction-set-3.bin",
        "mime": "application/octet-stream",
        "path": str(export_path),
    }


def test_reaction_export_download_returns_none_for_missing_output_file(tmp_path):
    from app import frontend_api

    missing_path = tmp_path / "missing.txt"

    assert frontend_api.reaction_export_download({"output_path": str(missing_path)}) is None


def test_reaction_export_download_rejects_symlinked_output_file(tmp_path):
    from app import frontend_api

    outside_path = tmp_path / "outside-secret.txt"
    outside_path.write_text("secret export\n", encoding="utf-8")
    export_path = tmp_path / "reaction-set-3.txt"
    export_path.symlink_to(outside_path)

    download = frontend_api.reaction_export_download(
        {
            "output_path": str(export_path),
            "mime_type": "text/plain",
        }
    )

    assert download is None


def test_reaction_export_download_returns_none_when_read_fails_after_safety_check(tmp_path, monkeypatch):
    from app import frontend_api

    missing_path = tmp_path / "raced.txt"
    monkeypatch.setattr(frontend_api, "is_safe_download_file", lambda path: True)

    download = frontend_api.reaction_export_download(
        {
            "output_path": str(missing_path),
            "mime_type": "text/plain",
        }
    )

    assert download is None


def test_reaction_set_review_state_blocks_empty_reaction_sets():
    from app import frontend_api

    state = frontend_api.reaction_set_review_state(
        {
            "id": 7,
            "status": "pending",
            "reaction_count": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "export_ready": False,
            "gas_mixture": "Ar/O2",
            "lxcat_db": "Biagi",
            "verified_by": None,
            "verified_at": None,
            "source_note": "Appendix table A1",
            "reactions": [],
        }
    )

    assert state == {
        "reactions": [],
        "unverified_reactions": [],
        "reaction_count": 0,
        "verified_count": 0,
        "unverified_count": 0,
        "export_ready": False,
        "export_blocked": True,
        "export_message": "没有可导出的反应。",
        "source_note": "Appendix table A1",
        "summary": (
            "status: pending · reactions: 0 · verified: 0 · 未复核: 0 · "
            "export_ready: False · gas_mixture: Ar/O2 · lxcat_db: Biagi · "
            "verified_by: - · verified_at: -"
        ),
    }


def test_reaction_set_review_state_derives_unverified_counts_and_export_gate():
    from app import frontend_api

    reactions = [
        {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True},
        {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False},
    ]

    state = frontend_api.reaction_set_review_state(
        {
            "status": "pending",
            "gas_mixture": None,
            "lxcat_db": None,
            "verified_by": "reviewer",
            "verified_at": "2026-06-26T10:00:00",
            "reactions": reactions,
        }
    )

    assert state["reactions"] == reactions
    assert state["unverified_reactions"] == [reactions[1]]
    assert state["reaction_count"] == 2
    assert state["verified_count"] == 1
    assert state["unverified_count"] == 1
    assert state["export_ready"] is False
    assert state["export_blocked"] is True
    assert state["export_message"] == "未全复核不可导出：请先完成所有反应复核。"
    assert state["summary"] == (
        "status: pending · reactions: 2 · verified: 1 · 未复核: 1 · "
        "export_ready: False · gas_mixture: - · lxcat_db: - · "
        "verified_by: reviewer · verified_at: 2026-06-26T10:00:00"
    )


def test_reaction_set_review_state_skips_malformed_reactions():
    from app import frontend_api

    valid_verified = {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True}
    valid_unverified = {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False}

    state = frontend_api.reaction_set_review_state(
        {
            "status": "pending",
            "reactions": ["bad-reaction", valid_verified, valid_unverified],
        }
    )

    assert state["reactions"] == [valid_verified, valid_unverified]
    assert state["unverified_reactions"] == [valid_unverified]
    assert state["reaction_count"] == 2
    assert state["verified_count"] == 1
    assert state["unverified_count"] == 1
    assert state["export_ready"] is False
    assert state["export_blocked"] is True


def test_reaction_set_review_state_skips_reactions_without_valid_id():
    from app import frontend_api

    valid_unverified = {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False}

    state = frontend_api.reaction_set_review_state(
        {
            "status": "pending",
            "reactions": [
                {"reaction": "missing id", "verified": False},
                {"id": "2", "reaction": "string id", "verified": False},
                {"id": True, "reaction": "bool id", "verified": False},
                valid_unverified,
            ],
        }
    )

    assert state["reactions"] == [valid_unverified]
    assert state["unverified_reactions"] == [valid_unverified]
    assert state["reaction_count"] == 1
    assert state["verified_count"] == 0
    assert state["unverified_count"] == 1
    assert state["export_blocked"] is True


def test_reaction_set_review_state_handles_malformed_counts_and_export_ready():
    from app import frontend_api

    reactions = [
        {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True},
        {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False},
    ]

    state = frontend_api.reaction_set_review_state(
        {
            "status": "pending",
            "reaction_count": ["2"],
            "verified_count": "1",
            "unverified_count": ["1"],
            "export_ready": "yes",
            "reactions": reactions,
        }
    )

    assert state["reaction_count"] == 2
    assert state["verified_count"] == 1
    assert state["unverified_count"] == 1
    assert state["export_ready"] is False
    assert state["export_blocked"] is True
    assert state["export_message"] == "未全复核不可导出：请先完成所有反应复核。"


def test_reaction_audit_rows_flatten_field_changes_for_review():
    from app import frontend_api

    rows = frontend_api.reaction_audit_rows(
        [
            {
                "id": 31,
                "reaction_id": 7,
                "verified_by": "engineer_a",
                "verified_at": "2026-06-25T10:00:00",
                "field_changes": {
                    "reaction_type": {"before": "unknown", "after": "ionization"},
                    "rate_value": {"before": None, "after": "1.2e-8 cm3/s"},
                    "verified": {"before": False, "after": True},
                },
            },
            {
                "id": 32,
                "reaction_id": 7,
                "verified_by": "engineer_b",
                "verified_at": "2026-06-26T11:00:00",
                "field_changes": {},
            },
        ]
    )

    assert rows == [
        {
            "audit_id": 31,
            "reaction_id": 7,
            "field": "reaction_type",
            "before": "unknown",
            "after": "ionization",
            "verified_by": "engineer_a",
            "verified_at": "2026-06-25T10:00:00",
        },
        {
            "audit_id": 31,
            "reaction_id": 7,
            "field": "rate_value",
            "before": "",
            "after": "1.2e-8 cm3/s",
            "verified_by": "engineer_a",
            "verified_at": "2026-06-25T10:00:00",
        },
        {
            "audit_id": 31,
            "reaction_id": 7,
            "field": "verified",
            "before": "False",
            "after": "True",
            "verified_by": "engineer_a",
            "verified_at": "2026-06-25T10:00:00",
        },
        {
            "audit_id": 32,
            "reaction_id": 7,
            "field": "-",
            "before": "",
            "after": "",
            "verified_by": "engineer_b",
            "verified_at": "2026-06-26T11:00:00",
        },
    ]


def test_reaction_audit_rows_handle_malformed_entries_and_field_changes():
    from app import frontend_api

    rows = frontend_api.reaction_audit_rows(
        [
            "bad-audit",
            {
                "id": 33,
                "reaction_id": 8,
                "verified_by": "engineer_c",
                "verified_at": "2026-06-27T12:00:00",
                "field_changes": ["bad-field-changes"],
            },
            {
                "id": 34,
                "reaction_id": 9,
                "verified_by": "engineer_d",
                "verified_at": "2026-06-27T13:00:00",
                "field_changes": {
                    "rate_value": ["bad-change"],
                    "verified": {"before": False, "after": True},
                },
            },
        ]
    )

    assert rows == [
        {
            "audit_id": None,
            "reaction_id": None,
            "field": "invalid",
            "before": "",
            "after": "",
            "verified_by": None,
            "verified_at": None,
        },
        {
            "audit_id": 33,
            "reaction_id": 8,
            "field": "field_changes",
            "before": "invalid",
            "after": "invalid",
            "verified_by": "engineer_c",
            "verified_at": "2026-06-27T12:00:00",
        },
        {
            "audit_id": 34,
            "reaction_id": 9,
            "field": "rate_value",
            "before": "invalid",
            "after": "invalid",
            "verified_by": "engineer_d",
            "verified_at": "2026-06-27T13:00:00",
        },
        {
            "audit_id": 34,
            "reaction_id": 9,
            "field": "verified",
            "before": "False",
            "after": "True",
            "verified_by": "engineer_d",
            "verified_at": "2026-06-27T13:00:00",
        },
    ]


def test_reaction_review_list_state_summarizes_filtered_review_scope():
    from app import frontend_api

    reactions = [
        {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True},
        {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False},
        {"id": 3, "reaction": "Ar+ + e -> Ar", "verified": False},
    ]

    state = frontend_api.reaction_review_list_state(reactions, only_unverified=True)

    assert state == {
        "display_reactions": [reactions[1], reactions[2]],
        "total_count": 3,
        "display_count": 2,
        "unverified_count": 2,
        "mode": "unverified",
        "summary": "当前显示未复核: 2/3 · 已隐藏已复核: 1",
    }


def test_reaction_review_list_state_summarizes_full_review_scope():
    from app import frontend_api

    reactions = [
        {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True},
        {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False},
    ]

    state = frontend_api.reaction_review_list_state(reactions, only_unverified=False)

    assert state == {
        "display_reactions": reactions,
        "total_count": 2,
        "display_count": 2,
        "unverified_count": 1,
        "mode": "all",
        "summary": "当前显示全部反应: 2 · 未复核: 1",
    }


def test_reaction_review_list_state_skips_malformed_reactions():
    from app import frontend_api

    valid_verified = {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True}
    valid_unverified = {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False}

    state = frontend_api.reaction_review_list_state(
        ["bad-reaction", valid_verified, valid_unverified],
        only_unverified=True,
    )

    assert state == {
        "display_reactions": [valid_unverified],
        "total_count": 2,
        "display_count": 1,
        "unverified_count": 1,
        "mode": "unverified",
        "summary": "当前显示未复核: 1/2 · 已隐藏已复核: 1",
    }


def test_reaction_review_list_state_skips_reactions_without_valid_id():
    from app import frontend_api

    valid_verified = {"id": 1, "reaction": "e + Ar -> e + Ar", "verified": True}
    valid_unverified = {"id": 2, "reaction": "e + Ar -> 2e + Ar+", "verified": False}

    state = frontend_api.reaction_review_list_state(
        [
            {"reaction": "missing id", "verified": False},
            {"id": "2", "reaction": "string id", "verified": False},
            {"id": False, "reaction": "bool id", "verified": False},
            valid_verified,
            valid_unverified,
        ],
        only_unverified=True,
    )

    assert state == {
        "display_reactions": [valid_unverified],
        "total_count": 2,
        "display_count": 1,
        "unverified_count": 1,
        "mode": "unverified",
        "summary": "当前显示未复核: 1/2 · 已隐藏已复核: 1",
    }


def test_crawl_job_rows_summarize_diagnostics_and_workflow_state():
    from app import frontend_api

    rows = frontend_api.crawl_job_rows(
        [
            {
                "id": 11,
                "journal_id": 2,
                "status": "success",
                "period": "manual",
                "date_from": "2026-01-01",
                "date_to": "2026-01-31",
                "journal": {"name": "Plasma Sources Science and Technology"},
                "diagnostics": {
                    "status": "success",
                    "period": "manual",
                    "date_from": "2026-01-01",
                    "date_to": "2026-01-31",
                    "papers_found": 12,
                    "papers_filtered": 4,
                    "papers_accepted": 8,
                    "papers_existing": 3,
                    "papers_new": 5,
                    "outcome": "new_papers",
                    "keyword_mode": "or",
                    "keyword_terms": ["plasma chemistry", "argon"],
                },
            },
            {
                "id": 12,
                "journal_id": 3,
                "status": "failed",
                "period": "weekly",
                "error": "OpenAlex timeout",
                "diagnostics": {"error": "OpenAlex timeout"},
            },
        ]
    )

    assert rows == [
        {
            "id": 11,
            "journal": "Plasma Sources Science and Technology",
            "status": "success",
            "workflow_state": "success",
            "period": "manual",
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
            "found": 12,
            "filtered": 4,
            "accepted": 8,
            "existing": 3,
            "new": 5,
            "progress_summary": "12 found / 8 accepted / 5 new",
            "outcome": "new_papers",
            "keyword_mode": "or",
            "keyword_terms": "plasma chemistry, argon",
            "error": None,
        },
        {
            "id": 12,
            "journal": 3,
            "status": "failed",
            "workflow_state": "failed: OpenAlex timeout",
            "period": "weekly",
            "date_from": None,
            "date_to": None,
            "found": 0,
            "filtered": 0,
            "accepted": 0,
            "existing": 0,
            "new": 0,
            "progress_summary": "0 found / 0 accepted / 0 new",
            "outcome": None,
            "keyword_mode": None,
            "keyword_terms": "",
            "error": "OpenAlex timeout",
        },
    ]


def test_crawl_job_rows_handle_malformed_diagnostics_counts():
    from app import frontend_api

    rows = frontend_api.crawl_job_rows(
        [
            {
                "id": 13,
                "journal_id": 4,
                "status": "success",
                "diagnostics": {
                    "papers_found": ["12"],
                    "papers_filtered": "4",
                    "papers_accepted": ["8"],
                    "papers_existing": "3",
                    "papers_new": ["5"],
                    "keyword_terms": {"term": "plasma"},
                },
            }
        ]
    )

    assert rows == [
        {
            "id": 13,
            "journal": 4,
            "status": "success",
            "workflow_state": "success",
            "period": None,
            "date_from": None,
            "date_to": None,
            "found": 0,
            "filtered": 0,
            "accepted": 0,
            "existing": 0,
            "new": 0,
            "progress_summary": "0 found / 0 accepted / 0 new",
            "outcome": None,
            "keyword_mode": None,
            "keyword_terms": "",
            "error": None,
        }
    ]


def test_crawl_job_rows_handle_malformed_nested_objects():
    from app import frontend_api

    rows = frontend_api.crawl_job_rows(
        [
            {
                "id": 14,
                "journal_id": 5,
                "status": "failed",
                "period": "manual",
                "error": "metadata source failed",
                "diagnostics": "bad-diagnostics",
                "journal": "bad-journal",
            }
        ]
    )

    assert rows == [
        {
            "id": 14,
            "journal": 5,
            "status": "failed",
            "workflow_state": "failed: metadata source failed",
            "period": "manual",
            "date_from": None,
            "date_to": None,
            "found": 0,
            "filtered": 0,
            "accepted": 0,
            "existing": 0,
            "new": 0,
            "progress_summary": "0 found / 0 accepted / 0 new",
            "outcome": None,
            "keyword_mode": None,
            "keyword_terms": "",
            "error": "metadata source failed",
        }
    ]


def test_crawl_job_diagnostic_rows_flatten_job_detail_for_review():
    from app import frontend_api

    rows = frontend_api.crawl_job_diagnostic_rows(
        {
            "id": 42,
            "journal_id": 7,
            "status": "failed",
            "period": "manual",
            "date_from": "2026-02-01",
            "date_to": "2026-02-28",
            "error": "Crossref returned 503",
            "journal": {"name": "Journal of Physics D"},
            "diagnostics": {
                "status": "failed",
                "journal_name": "Journal of Physics D",
                "papers_found": 18,
                "papers_filtered": 10,
                "papers_accepted": 8,
                "papers_existing": 6,
                "papers_new": 2,
                "outcome": "partial_failure",
                "keyword_mode": "and",
                "keyword_terms": ["plasma", "etching"],
                "error": "Crossref returned 503",
            },
        }
    )

    assert rows == [
        {"field": "job_id", "value": 42},
        {"field": "status", "value": "failed"},
        {"field": "journal", "value": "Journal of Physics D"},
        {"field": "period", "value": "manual"},
        {"field": "date_from", "value": "2026-02-01"},
        {"field": "date_to", "value": "2026-02-28"},
        {"field": "papers_found", "value": 18},
        {"field": "papers_filtered", "value": 10},
        {"field": "papers_accepted", "value": 8},
        {"field": "papers_existing", "value": 6},
        {"field": "papers_new", "value": 2},
        {"field": "outcome", "value": "partial_failure"},
        {"field": "keyword_mode", "value": "and"},
        {"field": "keyword_terms", "value": "plasma, etching"},
        {"field": "error", "value": "Crossref returned 503"},
    ]


def test_crawl_job_diagnostic_rows_handle_malformed_counts():
    from app import frontend_api

    rows = frontend_api.crawl_job_diagnostic_rows(
        {
            "id": 43,
            "journal_id": 7,
            "status": "success",
            "diagnostics": {
                "papers_found": ["18"],
                "papers_filtered": "10",
                "papers_accepted": ["8"],
                "papers_existing": "6",
                "papers_new": ["2"],
                "keyword_terms": {"term": "plasma"},
            },
        }
    )

    assert rows == [
        {"field": "job_id", "value": 43},
        {"field": "status", "value": "success"},
        {"field": "journal", "value": 7},
        {"field": "period", "value": None},
        {"field": "date_from", "value": None},
        {"field": "date_to", "value": None},
        {"field": "papers_found", "value": 0},
        {"field": "papers_filtered", "value": 0},
        {"field": "papers_accepted", "value": 0},
        {"field": "papers_existing", "value": 0},
        {"field": "papers_new", "value": 0},
        {"field": "outcome", "value": None},
        {"field": "keyword_mode", "value": None},
        {"field": "keyword_terms", "value": ""},
        {"field": "error", "value": None},
    ]


def test_crawl_job_diagnostic_rows_handle_malformed_nested_objects():
    from app import frontend_api

    rows = frontend_api.crawl_job_diagnostic_rows(
        {
            "id": 44,
            "journal_id": 8,
            "status": "failed",
            "period": "manual",
            "error": "Crossref returned malformed data",
            "diagnostics": "bad-diagnostics",
            "journal": "bad-journal",
        }
    )

    assert rows == [
        {"field": "job_id", "value": 44},
        {"field": "status", "value": "failed"},
        {"field": "journal", "value": 8},
        {"field": "period", "value": "manual"},
        {"field": "date_from", "value": None},
        {"field": "date_to", "value": None},
        {"field": "papers_found", "value": 0},
        {"field": "papers_filtered", "value": 0},
        {"field": "papers_accepted", "value": 0},
        {"field": "papers_existing", "value": 0},
        {"field": "papers_new", "value": 0},
        {"field": "outcome", "value": None},
        {"field": "keyword_mode", "value": None},
        {"field": "keyword_terms", "value": ""},
        {"field": "error", "value": "Crossref returned malformed data"},
    ]


def test_crawl_journal_options_label_whitelist_choices_for_manual_runs():
    from app import frontend_api

    options = frontend_api.crawl_journal_options(
        [
            {
                "id": 2,
                "name": "Plasma Sources Science and Technology",
                "issn_print": "0963-0252",
                "issn_electronic": "1361-6595",
            },
            {
                "id": 5,
                "name": "Journal of Physics D",
                "issn_print": None,
                "issn_electronic": "1361-6463",
            },
        ]
    )

    assert options == [
        {"label": "全部 active 期刊", "journal_id": None},
        {
            "label": "#2 · Plasma Sources Science and Technology · 0963-0252 / 1361-6595",
            "journal_id": 2,
        },
        {"label": "#5 · Journal of Physics D · 1361-6463", "journal_id": 5},
    ]


def test_crawl_journal_options_skips_malformed_journal_items():
    from app import frontend_api

    options = frontend_api.crawl_journal_options(
        [
            "bad",
            {"id": 8},
            {"id": 9, "name": "Valid Journal", "issn_print": None, "issn_electronic": None},
        ]
    )

    assert options == [
        {"label": "全部 active 期刊", "journal_id": None},
        {"label": "#9 · Valid Journal", "journal_id": 9},
    ]


def test_crawl_journal_option_label_returns_prebuilt_label():
    from app import frontend_api

    label = frontend_api.crawl_journal_option_label(
        {"label": "#2 · Plasma Sources Science and Technology", "journal_id": 2}
    )

    assert label == "#2 · Plasma Sources Science and Technology"


def test_crawl_journal_option_label_uses_fallback_for_missing_label():
    from app import frontend_api

    label = frontend_api.crawl_journal_option_label({"journal_id": None})

    assert label == "期刊选项"


def test_journal_option_label_summarizes_whitelist_status():
    from app import frontend_api

    label = frontend_api.journal_option_label(
        {"id": 4, "name": "Journal of Physics D", "active": True}
    )

    assert label == "#4 Journal of Physics D · active=True"


def test_journal_option_label_uses_unknown_name_and_false_active_fallback():
    from app import frontend_api

    label = frontend_api.journal_option_label({"id": 8})

    assert label == "#8 Journal · active=False"


def test_journal_option_label_handles_malformed_journal_items():
    from app import frontend_api

    label = frontend_api.journal_option_label({"name": ["Journal"], "active": "yes"})

    assert label == "#- Journal · active=False"


def test_paper_search_journal_options_skip_malformed_items():
    from app import frontend_api

    valid_journal = {"id": 2, "name": "Plasma Sources Science and Technology"}

    assert frontend_api.paper_search_journal_options(
        [
            "bad-journal",
            {"id": 3, "name": ""},
            {"id": "4", "name": "Journal of Physics D"},
            {"id": False, "name": "Bool Journal"},
            valid_journal,
        ]
    ) == [valid_journal]


def test_journal_items_skip_malformed_items():
    from app import frontend_api

    valid_journal = {"id": 2, "name": "Plasma Sources Science and Technology"}

    assert frontend_api.journal_items(
        [
            "bad-journal",
            {"id": 3, "name": ""},
            {"id": "4", "name": "Journal of Physics D"},
            {"id": False, "name": "Bool Journal"},
            valid_journal,
        ]
    ) == [valid_journal]


def test_paper_search_result_items_skip_malformed_items():
    from app import frontend_api

    valid_paper = {"id": 7, "title": "Ar/O2 plasma chemistry"}

    assert frontend_api.paper_search_result_items(
        [
            "bad-paper",
            {"title": "missing id"},
            {"id": "7", "title": "string id"},
            {"id": False, "title": "bool id"},
            {"id": 8, "title": ""},
            valid_paper,
        ]
    ) == [valid_paper]


def test_paper_search_response_state_handles_malformed_envelope():
    from app import frontend_api

    assert frontend_api.paper_search_response_state(
        {"items": "bad", "total": "7", "page": False, "page_size": -1}
    ) == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert frontend_api.paper_search_response_state(
        {
            "items": [{"id": 7, "title": "Ar/O2 plasma chemistry"}],
            "total": 1,
            "page": 2,
            "page_size": 10,
        }
    ) == {
        "items": [{"id": 7, "title": "Ar/O2 plasma chemistry"}],
        "total": 1,
        "page": 2,
        "page_size": 10,
    }


def test_crawl_jobs_response_state_handles_malformed_envelope():
    from app import frontend_api

    assert frontend_api.crawl_jobs_response_state(
        {"items": {"bad": "shape"}, "total": True, "page": 0, "page_size": "10"}
    ) == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert frontend_api.crawl_jobs_response_state(
        {
            "items": [{"id": 11, "status": "success"}],
            "total": 1,
            "page": 3,
            "page_size": 5,
        }
    ) == {
        "items": [{"id": 11, "status": "success"}],
        "total": 1,
        "page": 3,
        "page_size": 5,
    }


def test_paper_search_dedupe_label_handles_malformed_values():
    from app import frontend_api

    assert frontend_api.paper_search_dedupe_label({"doi": "10.1000/plasma"}) == "10.1000/plasma"
    assert (
        frontend_api.paper_search_dedupe_label({"dedupe_key": "no-doi-fingerprint-abcdef"})
        == "no-doi-fingerprint-abcde"
    )
    assert frontend_api.paper_search_dedupe_label({"doi": 123, "dedupe_key": True}) == "-"
    assert frontend_api.paper_search_dedupe_label({"doi": ["bad"], "dedupe_key": "fallback-key"}) == "fallback-key"


def test_paper_search_abstract_preview_handles_malformed_values():
    from app import frontend_api

    assert frontend_api.paper_search_abstract_preview({"abstract": "x" * 405}) == "x" * 400
    assert frontend_api.paper_search_abstract_preview({"abstract": None}) == ""
    assert frontend_api.paper_search_abstract_preview({"abstract": True}) == ""
    assert frontend_api.paper_search_abstract_preview({"abstract": ["bad"]}) == ""


def test_journal_table_rows_skip_malformed_items_and_format_keywords():
    from app import frontend_api

    rows = frontend_api.journal_table_rows(
        [
            "bad-journal",
            {
                "id": 2,
                "name": "Plasma Sources Science and Technology",
                "keywords": {"mode": "or", "terms": ["plasma", "etching"]},
            },
            {
                "id": 3,
                "name": "Journal of Physics D",
                "keywords": ["argon", "oxygen"],
            },
            {
                "id": 4,
                "name": "Sparse Journal",
                "keywords": None,
            },
        ]
    )

    assert rows == [
        {
            "id": 2,
            "name": "Plasma Sources Science and Technology",
            "keywords": '{"mode": "or", "terms": ["plasma", "etching"]}',
        },
        {
            "id": 3,
            "name": "Journal of Physics D",
            "keywords": '["argon", "oxygen"]',
        },
        {
            "id": 4,
            "name": "Sparse Journal",
            "keywords": None,
        },
    ]


def test_category_parent_option_label_returns_none_label():
    from app import frontend_api

    label = frontend_api.category_parent_option_label(None)

    assert label == "无"


def test_category_parent_options_skip_malformed_items():
    from app import frontend_api

    options = frontend_api.category_parent_options(
        [
            "bad-category",
            {"slug": "missing-id"},
            {"id": "1", "slug": "string-id"},
            {"id": False, "slug": "bool-id"},
            {"id": 1, "slug": "chemistry"},
            ["also-bad"],
            {"id": 2, "slug": "etching"},
        ]
    )

    assert options == [None, {"id": 1, "slug": "chemistry"}, {"id": 2, "slug": "etching"}]


def test_category_parent_option_label_summarizes_category_identity():
    from app import frontend_api

    label = frontend_api.category_parent_option_label(
        {"id": 3, "slug": "chemistry", "name": "等离子体化学"}
    )

    assert label == "#3 chemistry"


def test_category_parent_option_label_handles_malformed_category_items():
    from app import frontend_api

    label = frontend_api.category_parent_option_label({"slug": ["chemistry"]})

    assert label == "#- category"


def test_category_parent_option_label_handles_non_object_item():
    from app import frontend_api

    label = frontend_api.category_parent_option_label("bad-category")

    assert label == "#- category"


def test_paper_category_option_label_summarizes_slug_and_name():
    from app import frontend_api

    label = frontend_api.paper_category_option_label(
        {"id": 2, "slug": "chemistry", "name": "等离子体化学"}
    )

    assert label == "chemistry · 等离子体化学"


def test_paper_category_option_label_uses_fallback_name():
    from app import frontend_api

    label = frontend_api.paper_category_option_label({"id": 9, "slug": "methods"})

    assert label == "methods · category"


def test_paper_category_options_skip_malformed_items():
    from app import frontend_api

    valid_category = {"id": 2, "slug": "chemistry", "name": "等离子体化学"}

    assert frontend_api.paper_category_options(
        [
            "bad-category",
            {"id": 3, "name": "missing slug"},
            {"slug": "missing-id"},
            valid_category,
            None,
        ]
    ) == [valid_category]


def test_paper_category_slugs_skip_malformed_categories():
    from app import frontend_api

    assert frontend_api.paper_category_slugs({"categories": True}) == set()
    assert frontend_api.paper_category_slugs(
        {"categories": ["chemistry", "", ["bad"], {"slug": "bad"}, "etching"]}
    ) == {"chemistry", "etching"}


def test_paper_category_option_label_handles_non_object_item():
    from app import frontend_api

    label = frontend_api.paper_category_option_label("bad-category")

    assert label == "category · category"


def test_format_category_summary_handles_malformed_details():
    from app import frontend_api

    assert frontend_api.format_category_summary(
        {
            "category_details": [
                "bad-category",
                {"slug": "chemistry", "method": "auto", "confidence": 0.875},
                {"slug": "methods", "method": "", "confidence": "high"},
                {"method": "manual", "confidence": None},
            ],
            "categories": ["fallback"],
        }
    ) == "chemistry · auto · 0.88, methods · - · -, category · manual · -"


def test_format_category_summary_falls_back_to_category_slugs():
    from app import frontend_api

    assert frontend_api.format_category_summary({"category_details": ["bad"], "categories": ["chemistry"]}) == "chemistry"
    assert frontend_api.format_category_summary({"category_details": [], "categories": []}) == "-"


def test_paper_upload_option_label_returns_unlinked_choice():
    from app import frontend_api

    label = frontend_api.paper_upload_option_label(None)

    assert label == "不关联论文"


def test_paper_upload_options_skip_malformed_papers():
    from app import frontend_api

    valid_paper = {"id": 42, "title": "Ar/O2 ICP chemistry"}

    assert frontend_api.paper_upload_options(
        [
            "bad-paper",
            {"title": "missing id"},
            {"id": "42", "title": "string id"},
            {"id": False, "title": "bool id"},
            valid_paper,
            None,
        ]
    ) == [None, valid_paper]


def test_paper_upload_option_label_summarizes_paper_identity():
    from app import frontend_api

    label = frontend_api.paper_upload_option_label(
        {
            "id": 42,
            "title": "Ar/O2 ICP chemistry",
            "doi": "10.1234/plasma",
            "journal_name": "Plasma Sources Science and Technology",
            "published_date": "2026-06-01",
        }
    )

    assert label == "#42 · Ar/O2 ICP chemistry · DOI: 10.1234/plasma · Plasma Sources Science and Technology · 2026-06-01"


def test_paper_upload_option_label_uses_sparse_fallbacks():
    from app import frontend_api

    label = frontend_api.paper_upload_option_label({"id": 7})

    assert label == "#7 · Untitled · DOI: - · - · -"


def test_paper_upload_option_label_handles_malformed_paper():
    from app import frontend_api

    assert frontend_api.paper_upload_option_label("bad-paper") == "#- · Untitled · DOI: - · - · -"


def test_paper_upload_query_params_include_trimmed_search_text():
    from app import frontend_api

    params = frontend_api.paper_upload_query_params("  Ar/O2 ICP  ")

    assert params == {"page": 1, "page_size": 100, "q": "Ar/O2 ICP"}


def test_paper_upload_query_params_omit_blank_search_text():
    from app import frontend_api

    params = frontend_api.paper_upload_query_params("   ")

    assert params == {"page": 1, "page_size": 100}


def test_document_upload_success_state_blocks_malformed_success_payloads():
    from app import frontend_api

    assert frontend_api.document_upload_success_state({"id": 12}) == {
        "message": "document #12",
        "warning": None,
    }
    assert frontend_api.document_upload_success_state({"id": True}) == {
        "message": "document #unknown",
        "warning": "document upload response: invalid",
    }
    assert frontend_api.document_upload_success_state(["document"]) == {
        "message": "document #unknown",
        "warning": "document upload response: invalid",
    }


def test_document_status_filter_options_cover_actionable_workflows():
    from app import frontend_api

    assert frontend_api.document_status_filter_options() == [
        "全部",
        "待解析",
        "解析中",
        "解析失败",
        "待索引",
        "索引中",
        "索引失败",
        "待抽取",
        "抽取中",
        "抽取失败",
        "抽取被拒绝",
    ]


def test_filter_documents_by_status_matches_selected_workflow_state():
    from app import frontend_api

    documents = [
        {"id": 1, "parse_status": "uploaded", "index_status": "not_indexed", "chemistry_status": "not_extracted"},
        {"id": 2, "parse_status": "failed", "index_status": "failed", "chemistry_status": "failed"},
        {"id": 3, "parse_status": "parsed", "index_status": "indexed", "chemistry_status": "extracted"},
        {"id": 4, "parse_status": "parsing", "index_status": "indexing", "chemistry_status": "extracting"},
        {"id": 5, "parse_status": "parsed", "index_status": "indexed", "chemistry_status": "rejected"},
    ]

    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "全部")] == [1, 2, 3, 4, 5]
    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "解析失败")] == [2]
    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "待索引")] == [1]
    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "抽取中")] == [4]
    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "抽取被拒绝")] == [5]


def test_documents_response_state_handles_malformed_envelope():
    from app import frontend_api

    assert frontend_api.documents_response_state(
        {"items": {"bad": "shape"}, "total": "3", "page": True, "page_size": 0}
    ) == {"items": [], "total": 0, "page": 1, "page_size": 20}
    assert frontend_api.documents_response_state(
        {
            "items": [{"id": 5, "original_name": "argon.pdf"}],
            "total": 1,
            "page": 4,
            "page_size": 25,
        }
    ) == {
        "items": [{"id": 5, "original_name": "argon.pdf"}],
        "total": 1,
        "page": 4,
        "page_size": 25,
    }


def test_filter_documents_by_status_skips_malformed_documents():
    from app import frontend_api

    documents = [
        "bad-document",
        {"id": 1, "parse_status": "uploaded", "index_status": "not_indexed", "chemistry_status": "not_extracted"},
        {"id": 2, "parse_status": "failed", "index_status": "failed", "chemistry_status": "failed"},
    ]

    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "全部")] == [1, 2]
    assert [document["id"] for document in frontend_api.filter_documents_by_status(documents, "解析失败")] == [2]


def test_filter_documents_by_status_skips_documents_without_valid_id():
    from app import frontend_api

    valid_document = {
        "id": 3,
        "parse_status": "parsed",
        "index_status": "indexed",
        "chemistry_status": "extracted",
    }

    documents = [
        {"parse_status": "parsed", "index_status": "indexed", "chemistry_status": "extracted"},
        {"id": "3", "parse_status": "parsed", "index_status": "indexed", "chemistry_status": "extracted"},
        {"id": True, "parse_status": "parsed", "index_status": "indexed", "chemistry_status": "extracted"},
        valid_document,
    ]

    assert frontend_api.filter_documents_by_status(documents, "全部") == [valid_document]
    assert frontend_api.filter_documents_by_status(documents, "待索引") == []


def test_document_filter_summary_reports_current_page_match_count():
    from app import frontend_api

    summary = frontend_api.document_filter_summary(total_count=12, filtered_count=3, filter_value="解析失败")

    assert summary == "当前页匹配 3/12 · 筛选: 解析失败"


def test_document_option_label_surfaces_processing_states():
    from app import frontend_api

    label = frontend_api.document_option_label(
        {
            "id": 9,
            "original_name": "argon-kinetics.pdf",
            "file_path": "/tmp/uploads/argon-kinetics.pdf",
            "parse_status": "parsed",
            "index_status": "indexed",
            "chemistry_status": "extracted",
        }
    )

    assert label == "#9 · argon-kinetics.pdf · parse=parsed · index=indexed · chemistry=extracted"


def test_document_option_label_includes_linked_paper_identity():
    from app import frontend_api

    label = frontend_api.document_option_label(
        {
            "id": 9,
            "original_name": "argon-kinetics.pdf",
            "parse_status": "parsed",
            "index_status": "indexed",
            "chemistry_status": "extracted",
            "paper": {
                "title": "Global model of an Ar/O2 inductively coupled plasma",
                "doi": "10.1088/1361-6595/fixture-ar-o2",
            },
        }
    )

    assert (
        label
        == "#9 · argon-kinetics.pdf · Global model of an Ar/O2 inductively coupled plasma · "
        "DOI: 10.1088/1361-6595/fixture-ar-o2 · parse=parsed · index=indexed · chemistry=extracted"
    )


def test_document_option_label_falls_back_to_file_name_and_unknown_states():
    from app import frontend_api

    label = frontend_api.document_option_label({"id": 10, "file_path": "/tmp/uploads/no-name.pdf"})

    assert label == "#10 · no-name.pdf · parse=unknown · index=unknown · chemistry=unknown"


def test_document_option_label_handles_malformed_document():
    from app import frontend_api

    assert frontend_api.document_option_label("bad-document") == "#- · document · parse=unknown · index=unknown · chemistry=unknown"


def test_document_status_rows_summarize_document_workflow_and_errors():
    from app import frontend_api

    rows = frontend_api.document_status_rows(
        {
            "id": 12,
            "parse_status": "failed",
            "parse_error": "GROBID timeout",
            "index_status": "not_indexed",
            "index_error": None,
            "chemistry_status": "failed",
            "chemistry_error": "no parsed sections",
        },
        {"index_status": "failed", "index_error": "embedding unavailable", "total": 3},
    )

    assert rows == [
        {"field": "document_id", "value": 12},
        {"field": "parse_status", "value": "failed"},
        {"field": "parse_error", "value": "GROBID timeout"},
        {"field": "index_status", "value": "failed"},
        {"field": "index_error", "value": "embedding unavailable"},
        {"field": "chunks_total", "value": 3},
        {"field": "chemistry_status", "value": "failed"},
        {"field": "chemistry_error", "value": "no parsed sections"},
    ]


def test_document_status_rows_handle_malformed_chunks_total():
    from app import frontend_api

    rows = frontend_api.document_status_rows(
        {"id": 13, "parse_status": "parsed", "index_status": "indexed", "chemistry_status": "extracted"},
        {"index_status": "indexed", "total": ["3"]},
    )

    assert rows == [
        {"field": "document_id", "value": 13},
        {"field": "parse_status", "value": "parsed"},
        {"field": "parse_error", "value": None},
        {"field": "index_status", "value": "indexed"},
        {"field": "index_error", "value": None},
        {"field": "chunks_total", "value": 0},
        {"field": "chemistry_status", "value": "extracted"},
        {"field": "chemistry_error", "value": None},
    ]


def test_dataframe_display_rows_normalize_mixed_value_column_for_streamlit():
    from app import frontend_api

    rows = frontend_api.dataframe_display_rows(
        [
            {"field": "document_id", "value": 12},
            {"field": "parse_status", "value": "failed"},
            {"field": "parse_error", "value": None},
        ]
    )

    assert rows == [
        {"field": "document_id", "value": "12"},
        {"field": "parse_status", "value": "failed"},
        {"field": "parse_error", "value": ""},
    ]


def test_dataframe_display_rows_preserve_non_value_columns():
    from app import frontend_api

    rows = frontend_api.dataframe_display_rows([{"id": 1, "status": "ok"}])

    assert rows == [{"id": 1, "status": "ok"}]


def test_document_section_rows_surface_location_and_preview():
    from app import frontend_api

    rows = frontend_api.document_section_rows(
        [
            {
                "id": 21,
                "document_id": 5,
                "seq": 2,
                "section_type": "body",
                "title": "Reaction kinetics",
                "content": "  Electron impact ionization controls the density.  " * 20,
            },
            {
                "id": 22,
                "document_id": 5,
                "section_type": "table",
                "content": "",
            },
        ]
    )

    assert rows == [
        {
            "id": 21,
            "document_id": 5,
            "seq": 2,
            "section_type": "body",
            "title": "Reaction kinetics",
            "section_location": "section 2 · body · Reaction kinetics",
            "content_preview": (
                "Electron impact ionization controls the density. Electron impact ionization controls the "
                "density. Electron impact ionization controls the density. Electron impa..."
            ),
            "content_chars": 1040,
        },
        {
            "id": 22,
            "document_id": 5,
            "seq": None,
            "section_type": "table",
            "title": None,
            "section_location": "section 22 · table",
            "content_preview": "",
            "content_chars": 0,
        },
    ]


def test_document_section_rows_handle_malformed_entries_and_content():
    from app import frontend_api

    rows = frontend_api.document_section_rows(
        [
            "bad-section",
            {
                "id": 23,
                "document_id": 5,
                "seq": 3,
                "section_type": "body",
                "title": "Malformed content",
                "content": ["not", "text"],
            },
            {
                "id": 24,
                "document_id": 5,
                "seq": 4,
                "section_type": "body",
                "title": "Valid content",
                "content": "Electron density remains stable.",
            },
        ]
    )

    assert rows == [
        {
            "id": None,
            "document_id": None,
            "seq": None,
            "section_type": "invalid",
            "title": None,
            "section_location": "invalid",
            "content_preview": "invalid",
            "content_chars": 0,
        },
        {
            "id": 23,
            "document_id": 5,
            "seq": 3,
            "section_type": "body",
            "title": "Malformed content",
            "section_location": "section 3 · body · Malformed content",
            "content_preview": "invalid",
            "content_chars": 0,
        },
        {
            "id": 24,
            "document_id": 5,
            "seq": 4,
            "section_type": "body",
            "title": "Valid content",
            "section_location": "section 4 · body · Valid content",
            "content_preview": "Electron density remains stable.",
            "content_chars": 32,
        },
    ]


def test_document_section_option_label_uses_sequence_and_title():
    from app import frontend_api

    label = frontend_api.document_section_option_label(
        {"id": 21, "seq": 2, "title": "Reaction kinetics", "section_type": "body"}
    )

    assert label == "2. Reaction kinetics"


def test_document_section_option_label_falls_back_to_type_and_id():
    from app import frontend_api

    label = frontend_api.document_section_option_label({"id": 22, "section_type": "table"})

    assert label == "22. table"


def test_document_section_option_label_handles_malformed_section():
    from app import frontend_api

    assert frontend_api.document_section_option_label("bad-section") == "invalid. Section"


def test_document_section_preview_fields_handle_malformed_section_and_content():
    from app import frontend_api

    assert frontend_api.document_section_preview_title("bad-section") == "Section"
    assert frontend_api.document_section_preview_content("bad-section") == ""
    assert frontend_api.document_section_preview_title({"title": ["not", "text"]}) == "Section"
    assert frontend_api.document_section_preview_content({"content": ["not", "text"]}) == ""
    assert frontend_api.document_section_preview_title({"title": "Reaction kinetics"}) == "Reaction kinetics"
    assert frontend_api.document_section_preview_content({"content": "Electron density remains stable."}) == (
        "Electron density remains stable."
    )


def test_document_chunk_rows_surface_vector_backlinks_and_preview():
    from app import frontend_api

    rows = frontend_api.document_chunk_rows(
        [
            {
                "id": 31,
                "document_id": 5,
                "section_id": 21,
                "section_seq": 2,
                "section_title": "Reaction kinetics",
                "vector_id": "doc-5-section-21-chunk-31",
                "text": "Ar + e -> Ar+ + 2e is listed in the extracted table.",
            },
            {
                "id": 32,
                "section_id": 22,
                "text": None,
            },
        ]
    )

    assert rows == [
        {
            "id": 31,
            "document_id": 5,
            "section_id": 21,
            "section_seq": 2,
            "section_title": "Reaction kinetics",
            "vector_id": "doc-5-section-21-chunk-31",
            "chunk_location": "section 2 · Reaction kinetics · vector doc-5-section-21-chunk-31",
            "text_preview": "Ar + e -> Ar+ + 2e is listed in the extracted table.",
            "text_chars": 52,
        },
        {
            "id": 32,
            "document_id": None,
            "section_id": 22,
            "section_seq": None,
            "section_title": None,
            "vector_id": None,
            "chunk_location": "section 22",
            "text_preview": "",
            "text_chars": 0,
        },
    ]


def test_document_chunk_rows_handle_malformed_entries_and_text():
    from app import frontend_api

    rows = frontend_api.document_chunk_rows(
        [
            "bad-chunk",
            {
                "id": 33,
                "document_id": 5,
                "section_id": 23,
                "section_seq": 3,
                "section_title": "Malformed chunk",
                "vector_id": "doc-5-section-23-chunk-33",
                "text": ["not", "text"],
            },
            {
                "id": 34,
                "document_id": 5,
                "section_id": 24,
                "section_seq": 4,
                "section_title": "Valid chunk",
                "text": "Electron kinetics evidence.",
            },
        ]
    )

    assert rows == [
        {
            "id": None,
            "document_id": None,
            "section_id": None,
            "section_seq": None,
            "section_title": None,
            "vector_id": None,
            "chunk_location": "invalid",
            "text_preview": "invalid",
            "text_chars": 0,
        },
        {
            "id": 33,
            "document_id": 5,
            "section_id": 23,
            "section_seq": 3,
            "section_title": "Malformed chunk",
            "vector_id": "doc-5-section-23-chunk-33",
            "chunk_location": "section 3 · Malformed chunk · vector doc-5-section-23-chunk-33",
            "text_preview": "invalid",
            "text_chars": 0,
        },
        {
            "id": 34,
            "document_id": 5,
            "section_id": 24,
            "section_seq": 4,
            "section_title": "Valid chunk",
            "vector_id": None,
            "chunk_location": "section 4 · Valid chunk",
            "text_preview": "Electron kinetics evidence.",
            "text_chars": 27,
        },
    ]


def test_document_chunk_option_label_uses_vector_and_section_title():
    from app import frontend_api

    label = frontend_api.document_chunk_option_label(
        {"id": 31, "vector_id": "doc-5-section-21-chunk-31", "section_title": "Reaction kinetics"}
    )

    assert label == "doc-5-section-21-chunk-31 · Reaction kinetics"


def test_document_chunk_option_label_falls_back_to_id_and_dash_title():
    from app import frontend_api

    label = frontend_api.document_chunk_option_label({"id": 32})

    assert label == "32 · -"


def test_document_chunk_option_label_handles_malformed_chunk():
    from app import frontend_api

    assert frontend_api.document_chunk_option_label("bad-chunk") == "invalid · -"


def test_document_chunk_preview_text_handles_malformed_chunk_and_text():
    from app import frontend_api

    assert frontend_api.document_chunk_preview_text("bad-chunk") == ""
    assert frontend_api.document_chunk_preview_text({"text": ["not", "text"]}) == ""
    assert frontend_api.document_chunk_preview_text({"text": "Electron kinetics evidence."}) == "Electron kinetics evidence."


def test_document_asset_downloads_read_pdf_bytes_and_tei_text(tmp_path):
    from app import frontend_api

    pdf_path = tmp_path / "paper.pdf"
    tei_path = tmp_path / "paper.tei.xml"
    pdf_path.write_bytes(b"%PDF plasma")
    tei_path.write_text("<TEI>plasma</TEI>", encoding="utf-8")

    downloads = frontend_api.document_asset_downloads(
        {"file_path": str(pdf_path), "tei_path": str(tei_path)}
    )

    assert downloads == [
        {
            "kind": "pdf",
            "label": "下载原始 PDF",
            "data": b"%PDF plasma",
            "file_name": "paper.pdf",
            "mime": "application/pdf",
            "path": str(pdf_path),
            "exists": True,
            "missing_message": None,
        },
        {
            "kind": "tei",
            "label": "下载 TEI XML",
            "data": "<TEI>plasma</TEI>",
            "file_name": "paper.tei.xml",
            "mime": "application/xml",
            "path": str(tei_path),
            "exists": True,
            "missing_message": None,
        },
    ]


def test_document_asset_downloads_report_missing_files(tmp_path):
    from app import frontend_api

    missing_pdf = tmp_path / "missing.pdf"
    missing_tei = tmp_path / "missing.tei.xml"

    downloads = frontend_api.document_asset_downloads(
        {"file_path": str(missing_pdf), "tei_path": str(missing_tei)}
    )

    assert downloads == [
        {
            "kind": "pdf",
            "label": "下载原始 PDF",
            "data": None,
            "file_name": "missing.pdf",
            "mime": "application/pdf",
            "path": str(missing_pdf),
            "exists": False,
            "missing_message": f"PDF 文件不存在: {missing_pdf}",
        },
        {
            "kind": "tei",
            "label": "下载 TEI XML",
            "data": None,
            "file_name": "missing.tei.xml",
            "mime": "application/xml",
            "path": str(missing_tei),
            "exists": False,
            "missing_message": f"TEI 文件不存在: {missing_tei}",
        },
    ]


def test_document_asset_downloads_reject_symlinked_files(tmp_path):
    from app import frontend_api

    outside_pdf = tmp_path / "outside.pdf"
    outside_pdf.write_bytes(b"%PDF secret")
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.symlink_to(outside_pdf)
    outside_tei = tmp_path / "outside.tei.xml"
    outside_tei.write_text("<TEI>secret</TEI>", encoding="utf-8")
    tei_path = tmp_path / "paper.tei.xml"
    tei_path.symlink_to(outside_tei)

    downloads = frontend_api.document_asset_downloads(
        {"file_path": str(pdf_path), "tei_path": str(tei_path)}
    )

    assert downloads == [
        {
            "kind": "pdf",
            "label": "下载原始 PDF",
            "data": None,
            "file_name": "paper.pdf",
            "mime": "application/pdf",
            "path": str(pdf_path),
            "exists": False,
            "missing_message": f"PDF 文件不存在: {pdf_path}",
        },
        {
            "kind": "tei",
            "label": "下载 TEI XML",
            "data": None,
            "file_name": "paper.tei.xml",
            "mime": "application/xml",
            "path": str(tei_path),
            "exists": False,
            "missing_message": f"TEI 文件不存在: {tei_path}",
        },
    ]


def test_document_asset_downloads_report_missing_when_read_fails_after_safety_check(tmp_path, monkeypatch):
    from app import frontend_api

    missing_pdf = tmp_path / "raced.pdf"
    missing_tei = tmp_path / "raced.tei.xml"
    monkeypatch.setattr(frontend_api, "is_safe_download_file", lambda path: True)

    downloads = frontend_api.document_asset_downloads(
        {"file_path": str(missing_pdf), "tei_path": str(missing_tei)}
    )

    assert downloads == [
        {
            "kind": "pdf",
            "label": "下载原始 PDF",
            "data": None,
            "file_name": "raced.pdf",
            "mime": "application/pdf",
            "path": str(missing_pdf),
            "exists": False,
            "missing_message": f"PDF 文件不存在: {missing_pdf}",
        },
        {
            "kind": "tei",
            "label": "下载 TEI XML",
            "data": None,
            "file_name": "raced.tei.xml",
            "mime": "application/xml",
            "path": str(missing_tei),
            "exists": False,
            "missing_message": f"TEI 文件不存在: {missing_tei}",
        },
    ]


def test_frontend_download_allows_system_root_symlink_parent():
    import tempfile
    from pathlib import Path

    import pytest

    from app import frontend_api

    var_path = Path("/var")
    if not var_path.is_symlink():
        pytest.skip("/var is not a symlink on this platform")

    with tempfile.TemporaryDirectory(dir="/var/tmp") as temp_dir:
        download_path = Path(temp_dir) / "paper.tei.xml"
        download_path.write_text("<TEI>plasma</TEI>", encoding="utf-8")

        assert str(download_path).startswith("/var/")
        assert frontend_api.is_safe_download_file(download_path) is True


def test_translation_status_rows_summarize_output_file_preview():
    from app import frontend_api

    rows = frontend_api.translation_status_rows(
        {
            "document_id": 5,
            "status": "translated",
            "target_lang": "zh",
            "output_path": "/tmp/translations/doc-5.zh.md",
            "error": None,
        },
        preview_text="# Title\n\n" + "Translated plasma paragraph. " * 30,
    )

    assert rows == [
        {"field": "document_id", "value": 5},
        {"field": "status", "value": "translated"},
        {"field": "target_lang", "value": "zh"},
        {"field": "output_path", "value": "/tmp/translations/doc-5.zh.md"},
        {"field": "error", "value": None},
        {"field": "preview_chars", "value": 879},
        {
            "field": "preview",
            "value": (
                "# Title Translated plasma paragraph. Translated plasma paragraph. Translated plasma "
                "paragraph. Translated plasma paragraph. Translated plasma paragraph. Transla..."
            ),
        },
    ]


def test_translation_status_rows_handle_malformed_preview_text():
    from app import frontend_api

    rows = frontend_api.translation_status_rows(
        {
            "document_id": 5,
            "status": "failed",
            "target_lang": "zh",
            "output_path": "/tmp/translations/doc-5.zh.md",
            "error": "preview read returned non-text",
        },
        preview_text=["not", "text"],
    )

    assert rows == [
        {"field": "document_id", "value": 5},
        {"field": "status", "value": "failed"},
        {"field": "target_lang", "value": "zh"},
        {"field": "output_path", "value": "/tmp/translations/doc-5.zh.md"},
        {"field": "error", "value": "preview read returned non-text"},
        {"field": "preview_chars", "value": 0},
        {"field": "preview", "value": "invalid"},
    ]


def test_translation_download_reads_markdown_for_streamlit_button(tmp_path):
    from app import frontend_api

    output_path = tmp_path / "document-5-zh.md"
    output_path.write_text("# Plasma\n\n等离子体翻译\n", encoding="utf-8")

    download = frontend_api.translation_download({"output_path": str(output_path)})

    assert download == {
        "label": "下载双语翻译",
        "data": "# Plasma\n\n等离子体翻译\n",
        "file_name": "document-5-zh.md",
        "mime": "text/markdown",
        "path": str(output_path),
    }


def test_translation_download_returns_none_for_missing_output_file(tmp_path):
    from app import frontend_api

    missing_path = tmp_path / "missing.md"

    assert frontend_api.translation_download({"output_path": str(missing_path)}) is None


def test_translation_download_rejects_symlinked_output_file(tmp_path):
    from app import frontend_api

    outside_path = tmp_path / "outside.md"
    outside_path.write_text("# Secret\n", encoding="utf-8")
    output_path = tmp_path / "document-5-zh.md"
    output_path.symlink_to(outside_path)

    assert frontend_api.translation_download({"output_path": str(output_path)}) is None


def test_translation_download_returns_none_when_read_fails_after_safety_check(tmp_path, monkeypatch):
    from app import frontend_api

    missing_path = tmp_path / "raced.md"
    monkeypatch.setattr(frontend_api, "is_safe_download_file", lambda path: True)

    assert frontend_api.translation_download({"output_path": str(missing_path)}) is None


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


def test_rag_source_rows_handle_malformed_source_entries():
    from app import frontend_api

    rows = frontend_api.rag_source_rows(
        [
            "bad-source",
            {
                "document_id": 4,
                "section_id": 20,
                "section_title": "Appendix",
                "source_excerpt": "valid appendix evidence",
            },
        ]
    )

    assert rows == [
        {
            "citation": "[invalid]",
            "source_location": "invalid",
            "document_id": None,
            "paper_id": None,
            "paper_title": None,
            "section_id": None,
            "section_seq": None,
            "section_title": None,
            "section_type": None,
            "source_excerpt": None,
            "chunk_id": None,
            "vector_id": None,
            "score": None,
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
            "source_excerpt": "valid appendix evidence",
            "chunk_id": None,
            "vector_id": None,
            "score": None,
        },
    ]


def test_rag_source_option_label_combines_citation_and_location():
    from app import frontend_api

    label = frontend_api.rag_source_option_label(
        {
            "citation": "[paper 7 · doc 3 · section 4 · chunk 19]",
            "source_location": "paper 7 · doc 3 · section 4 · table · Reaction table",
        }
    )

    assert label == "[paper 7 · doc 3 · section 4 · chunk 19] · paper 7 · doc 3 · section 4 · table · Reaction table"


def test_rag_source_option_label_handles_malformed_source():
    from app import frontend_api

    assert frontend_api.rag_source_option_label("bad-source") == "引用来源"


def test_rag_source_preview_excerpt_handles_malformed_source_and_excerpt():
    from app import frontend_api

    assert frontend_api.rag_source_preview_excerpt("bad-source") == ""
    assert frontend_api.rag_source_preview_excerpt({"source_excerpt": ["not", "text"]}) == ""
    assert frontend_api.rag_source_preview_excerpt({"source_excerpt": "e + Ar -> e + e + Ar+"}) == (
        "e + Ar -> e + e + Ar+"
    )


def test_rag_source_option_label_uses_stable_fallback():
    from app import frontend_api

    label = frontend_api.rag_source_option_label({})

    assert label == "引用来源"


def test_api_docs_links_use_service_root_when_api_base_includes_version_prefix():
    from app import frontend_api

    links = frontend_api.api_docs_links("http://127.0.0.1:8000/api/v1")

    assert links == {
        "OpenAPI JSON": "http://127.0.0.1:8000/openapi.json",
        "Swagger UI": "http://127.0.0.1:8000/docs",
        "ReDoc": "http://127.0.0.1:8000/redoc",
    }


def test_api_docs_links_preserve_custom_api_base_without_version_prefix():
    from app import frontend_api

    links = frontend_api.api_docs_links("https://paper-lab.example.test/custom-api/")

    assert links == {
        "OpenAPI JSON": "https://paper-lab.example.test/custom-api/openapi.json",
        "Swagger UI": "https://paper-lab.example.test/custom-api/docs",
        "ReDoc": "https://paper-lab.example.test/custom-api/redoc",
    }
