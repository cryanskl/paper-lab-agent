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


def test_crawl_job_option_label_summarizes_job_status():
    from app import frontend_api

    label = frontend_api.crawl_job_option_label({"id": 12, "journal_id": 3, "status": "success"})

    assert label == "#12 · journal 3 · success"


def test_crawl_job_option_label_uses_fallbacks_for_sparse_jobs():
    from app import frontend_api

    label = frontend_api.crawl_job_option_label({"job_id": 9})

    assert label == "#9 · journal - · unknown"


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


def test_reaction_set_option_label_summarizes_review_and_export_state():
    from app import frontend_api

    label = frontend_api.reaction_set_option_label(
        {
            "id": 3,
            "name": "Ar chemistry",
            "status": "pending",
            "export_ready": False,
            "unverified_count": 2,
        }
    )

    assert label == "#3 · pending · export_ready False · 未复核 2 · Ar chemistry"


def test_reaction_set_option_label_uses_fallbacks_for_sparse_items():
    from app import frontend_api

    label = frontend_api.reaction_set_option_label({"id": 8})

    assert label == "#8 · unknown · export_ready False · 未复核 0 · Reaction set"


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
            "before": None,
            "after": "1.2e-8 cm3/s",
            "verified_by": "engineer_a",
            "verified_at": "2026-06-25T10:00:00",
        },
        {
            "audit_id": 32,
            "reaction_id": 7,
            "field": "-",
            "before": None,
            "after": None,
            "verified_by": "engineer_b",
            "verified_at": "2026-06-26T11:00:00",
        },
    ]


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


def test_category_parent_option_label_returns_none_label():
    from app import frontend_api

    label = frontend_api.category_parent_option_label(None)

    assert label == "无"


def test_category_parent_option_label_summarizes_category_identity():
    from app import frontend_api

    label = frontend_api.category_parent_option_label(
        {"id": 3, "slug": "chemistry", "name": "等离子体化学"}
    )

    assert label == "#3 chemistry"


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


def test_document_option_label_falls_back_to_file_name_and_unknown_states():
    from app import frontend_api

    label = frontend_api.document_option_label({"id": 10, "file_path": "/tmp/uploads/no-name.pdf"})

    assert label == "#10 · no-name.pdf · parse=unknown · index=unknown · chemistry=unknown"


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


def test_rag_source_option_label_combines_citation_and_location():
    from app import frontend_api

    label = frontend_api.rag_source_option_label(
        {
            "citation": "[paper 7 · doc 3 · section 4 · chunk 19]",
            "source_location": "paper 7 · doc 3 · section 4 · table · Reaction table",
        }
    )

    assert label == "[paper 7 · doc 3 · section 4 · chunk 19] · paper 7 · doc 3 · section 4 · table · Reaction table"


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
