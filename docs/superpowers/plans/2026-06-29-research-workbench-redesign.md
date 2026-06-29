# Research Workbench Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the module-tab Streamlit frontend with a three-column research workbench for library intake, whole-knowledge-base Q&A, PDF analysis, and chemistry delivery.

**Architecture:** Keep the existing FastAPI API contract unchanged. Add small, tested state helpers to `app/frontend_api.py`, then refactor `streamlit_app.py` into render functions and compose them as a three-column desktop workbench. Move system diagnostics into a maintenance expander instead of the always-visible sidebar.

**Tech Stack:** Python, Streamlit, FastAPI client helpers in `app/frontend_api.py`, pytest, existing `scripts/health_check.py` and `scripts/release_check.sh`.

## Global Constraints

- Reuse the existing FastAPI contract and helper functions in `app/frontend_api.py`.
- Treat RAG as knowledge-base Q&A, not single-paper Q&A.
- Present chemistry extraction as part of PDF analysis and knowledge deposition, not as an isolated final step.
- Keep maintenance, raw JSON, API docs, release readiness, journals, and categories available but visually secondary.
- Preserve existing functionality and API behavior.
- Do not add user accounts, cloud sync, permissions, or collaboration.
- Do not change API paths, database schema, or response contracts.
- Do not introduce a new frontend framework.
- Do not make automatic background refresh the default behavior.
- Do not hide failure details needed for debugging; move them into maintenance or expandable diagnostics.
- Default RAG request uses `document_ids: []` unless the user explicitly scopes the query.
- Use a wide layout with three persistent columns: left about 28%, middle about 44%, right about 28%.

---

## File Structure

- Modify `app/frontend_api.py`: add pure helper functions for workbench status cards, RAG scoping, document analysis action labels, and chemistry deposition summaries. These helpers keep malformed payload handling testable outside Streamlit.
- Modify `tests/test_frontend_api.py`: add focused tests for the new helper functions.
- Modify `streamlit_app.py`: refactor existing top-level tab bodies into render functions, then compose the workbench with a top status strip, left library intake column, middle knowledge/analysis column, right chemistry delivery column, and a maintenance expander.
- No backend files should change.
- No schema or API contract docs should change.

---

### Task 1: Add Tested Workbench State Helpers

**Files:**
- Modify: `app/frontend_api.py`
- Modify: `tests/test_frontend_api.py`

**Interfaces:**
- Consumes: existing helper functions `dict_or_empty()`, `non_negative_int_or_zero()`, `release_readiness_display_state()`, `demo_data_display_state()`, `documents_response_state()`, `document_chunks_response_state()`, `reaction_set_review_state()`.
- Produces:
  - `workbench_status_cards(status: Any) -> list[dict[str, Any]]`
  - `rag_document_ids_for_scope(scope: str, selected_document_ids: list[int], typed_document_ids: list[int]) -> list[int]`
  - `document_analysis_steps(document: dict[str, Any], chunks: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]`
  - `chemistry_deposition_summary(detail: dict[str, Any]) -> dict[str, Any]`

- [ ] **Step 1: Append failing tests for status cards**

Add these tests to the end of `tests/test_frontend_api.py`:

```python
def test_workbench_status_cards_summarize_research_workbench_state():
    from app import frontend_api

    cards = frontend_api.workbench_status_cards(
        {
            "counts": {
                "papers": 12,
                "documents": 3,
                "chunks": 41,
                "reaction_sets": 2,
                "reactions": 9,
            },
            "status_counts": {
                "document_parse": {"parsed": 2, "failed": 1},
                "document_index": {"indexed": 2},
                "document_chemistry": {"extracted": 1, "failed": 1},
                "reaction_sets": {"pending": 1, "verified": 1},
            },
            "release_readiness": {
                "ready": True,
                "demo_data_missing": [],
                "failed_workflows": [],
                "config_warning_codes": ["missing_llm_api_key"],
                "storage_errors": [],
            },
            "config_warnings": [
                {"capability": "llm_translation", "message": "LLM_API_KEY is not configured."}
            ],
            "external_capabilities": {
                "grobid": {"available": False, "error": "connection refused"}
            },
        }
    )

    assert cards == [
        {"group": "知识库", "label": "论文", "value": "12", "state": "ok", "detail": "本地论文元数据"},
        {"group": "知识库", "label": "PDF", "value": "3", "state": "ok", "detail": "已导入文档"},
        {"group": "知识库", "label": "Chunks", "value": "41", "state": "ok", "detail": "可检索片段"},
        {"group": "PDF 分析", "label": "已解析", "value": "2", "state": "ok", "detail": "parsed"},
        {"group": "PDF 分析", "label": "已索引", "value": "2", "state": "ok", "detail": "indexed"},
        {"group": "PDF 分析", "label": "化学抽取", "value": "1", "state": "ok", "detail": "extracted"},
        {"group": "PDF 分析", "label": "失败", "value": "2", "state": "warning", "detail": "parse/index/chemistry failed"},
        {"group": "化学库", "label": "反应集", "value": "2", "state": "ok", "detail": "reaction sets"},
        {"group": "化学库", "label": "反应", "value": "9", "state": "ok", "detail": "extracted reactions"},
        {"group": "化学库", "label": "待复核", "value": "1", "state": "warning", "detail": "pending reaction sets"},
        {"group": "系统", "label": "发布状态", "value": "ready", "state": "ok", "detail": "release ready"},
        {"group": "系统", "label": "配置提示", "value": "1", "state": "warning", "detail": "non-blocking warnings"},
        {"group": "系统", "label": "GROBID", "value": "不可用", "state": "warning", "detail": "connection refused"},
    ]


def test_workbench_status_cards_reject_malformed_status_payload():
    from app import frontend_api

    cards = frontend_api.workbench_status_cards(["status"])

    assert cards[0] == {
        "group": "系统",
        "label": "状态",
        "value": "invalid",
        "state": "warning",
        "detail": "system status payload is invalid",
    }
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_frontend_api.py::test_workbench_status_cards_summarize_research_workbench_state tests/test_frontend_api.py::test_workbench_status_cards_reject_malformed_status_payload -q
```

Expected: both tests fail with `AttributeError: module 'app.frontend_api' has no attribute 'workbench_status_cards'`.

- [ ] **Step 3: Implement `workbench_status_cards()`**

Add this code to `app/frontend_api.py` after `config_warning_rows()`:

```python
def _workbench_count_label(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "invalid"
    return str(value)


def _workbench_count_state(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return "warning"
    return "ok"


def _workflow_count(status_counts: dict[str, Any], workflow: str, state: str) -> int:
    workflow_counts = status_counts.get(workflow)
    if not isinstance(workflow_counts, dict):
        return 0
    value = workflow_counts.get(state)
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def workbench_status_cards(status: Any) -> list[dict[str, Any]]:
    if not isinstance(status, dict):
        return [
            {
                "group": "系统",
                "label": "状态",
                "value": "invalid",
                "state": "warning",
                "detail": "system status payload is invalid",
            }
        ]

    counts = status.get("counts") if isinstance(status.get("counts"), dict) else {}
    status_counts = status.get("status_counts") if isinstance(status.get("status_counts"), dict) else {}
    release_display = release_readiness_display_state(status.get("release_readiness") or {})
    config_warnings = status.get("config_warnings") if isinstance(status.get("config_warnings"), list) else []
    external_display = external_capabilities_display_state(status.get("external_capabilities") or {})
    grobid = external_display.get("grobid") or {}

    parse_failed = _workflow_count(status_counts, "document_parse", "failed")
    index_failed = _workflow_count(status_counts, "document_index", "failed")
    chemistry_failed = _workflow_count(status_counts, "document_chemistry", "failed")
    failure_count = parse_failed + index_failed + chemistry_failed
    pending_reaction_sets = _workflow_count(status_counts, "reaction_sets", "pending")

    grobid_available = grobid.get("available")
    if grobid_available is True:
        grobid_value = "可用"
        grobid_state = "ok"
        grobid_detail = str(grobid.get("url") or "checked")
    elif grobid_available is False:
        grobid_value = "不可用"
        grobid_state = "warning"
        grobid_detail = str(grobid.get("error") or "checked unavailable")
    else:
        grobid_value = "未检查"
        grobid_state = "neutral"
        grobid_detail = str(grobid.get("url") or "not checked")

    release_ready = release_display.get("ready") is True
    cards = [
        {"group": "知识库", "label": "论文", "value": _workbench_count_label(counts.get("papers")), "state": _workbench_count_state(counts.get("papers")), "detail": "本地论文元数据"},
        {"group": "知识库", "label": "PDF", "value": _workbench_count_label(counts.get("documents")), "state": _workbench_count_state(counts.get("documents")), "detail": "已导入文档"},
        {"group": "知识库", "label": "Chunks", "value": _workbench_count_label(counts.get("chunks")), "state": _workbench_count_state(counts.get("chunks")), "detail": "可检索片段"},
        {"group": "PDF 分析", "label": "已解析", "value": str(_workflow_count(status_counts, "document_parse", "parsed")), "state": "ok", "detail": "parsed"},
        {"group": "PDF 分析", "label": "已索引", "value": str(_workflow_count(status_counts, "document_index", "indexed")), "state": "ok", "detail": "indexed"},
        {"group": "PDF 分析", "label": "化学抽取", "value": str(_workflow_count(status_counts, "document_chemistry", "extracted")), "state": "ok", "detail": "extracted"},
        {"group": "PDF 分析", "label": "失败", "value": str(failure_count), "state": "warning" if failure_count else "ok", "detail": "parse/index/chemistry failed"},
        {"group": "化学库", "label": "反应集", "value": _workbench_count_label(counts.get("reaction_sets")), "state": _workbench_count_state(counts.get("reaction_sets")), "detail": "reaction sets"},
        {"group": "化学库", "label": "反应", "value": _workbench_count_label(counts.get("reactions")), "state": _workbench_count_state(counts.get("reactions")), "detail": "extracted reactions"},
        {"group": "化学库", "label": "待复核", "value": str(pending_reaction_sets), "state": "warning" if pending_reaction_sets else "ok", "detail": "pending reaction sets"},
        {"group": "系统", "label": "发布状态", "value": "ready" if release_ready else "blocked", "state": "ok" if release_ready else "warning", "detail": "release ready" if release_ready else ", ".join(release_display.get("blockers") or ["ready=false"])},
        {"group": "系统", "label": "配置提示", "value": str(len(config_warnings)), "state": "warning" if config_warnings else "ok", "detail": "non-blocking warnings" if config_warnings else "configured"},
        {"group": "系统", "label": "GROBID", "value": grobid_value, "state": grobid_state, "detail": grobid_detail},
    ]
    return cards
```

- [ ] **Step 4: Append failing tests for RAG scope and document analysis**

Add these tests to the end of `tests/test_frontend_api.py`:

```python
def test_rag_document_ids_for_scope_defaults_to_whole_knowledge_base():
    from app import frontend_api

    assert frontend_api.rag_document_ids_for_scope("全部知识库", [7], [8]) == []
    assert frontend_api.rag_document_ids_for_scope("选中文档", [7], [8, 7]) == [7, 8]
    assert frontend_api.rag_document_ids_for_scope("手动范围", [7], [8, 9]) == [8, 9]
    assert frontend_api.rag_document_ids_for_scope("未知", [7], [8]) == []


def test_document_analysis_steps_group_existing_pdf_operations():
    from app import frontend_api

    steps = frontend_api.document_analysis_steps(
        {
            "parse_status": "parsed",
            "index_status": "not_indexed",
            "chemistry_status": "extracted",
            "parse_error": None,
            "index_error": None,
            "chemistry_error": None,
        },
        {"total": 5, "index_status": "not_indexed"},
    )

    assert steps == [
        {"key": "parse", "label": "解析章节", "status": "parsed", "state": "ok", "detail": "章节已解析"},
        {"key": "index", "label": "写入知识库", "status": "not_indexed", "state": "warning", "detail": "尚未建立可问答索引"},
        {"key": "translation", "label": "翻译预览", "status": "available_after_parse", "state": "neutral", "detail": "解析后可生成或查看翻译"},
        {"key": "chemistry", "label": "沉淀化学库", "status": "extracted", "state": "ok", "detail": "反应集已抽取"},
    ]
```

- [ ] **Step 5: Run tests to verify they fail**

Run:

```bash
python -m pytest tests/test_frontend_api.py::test_rag_document_ids_for_scope_defaults_to_whole_knowledge_base tests/test_frontend_api.py::test_document_analysis_steps_group_existing_pdf_operations -q
```

Expected: both tests fail with missing helper attributes.

- [ ] **Step 6: Implement RAG scope and document analysis helpers**

Add this code to `app/frontend_api.py` after `workbench_status_cards()`:

```python
def _positive_unique_ints(values: list[int]) -> list[int]:
    output: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            continue
        if value not in output:
            output.append(value)
    return output


def rag_document_ids_for_scope(scope: str, selected_document_ids: list[int], typed_document_ids: list[int]) -> list[int]:
    if scope == "选中文档":
        return _positive_unique_ints([*selected_document_ids, *typed_document_ids])
    if scope == "手动范围":
        return _positive_unique_ints(typed_document_ids)
    return []


def _analysis_state(status: Any, *, done_values: set[str], active_values: set[str], empty_detail: str, done_detail: str, active_detail: str, error: Any = None) -> dict[str, str]:
    normalized = status if isinstance(status, str) and status.strip() else "unknown"
    if normalized == "failed" or normalized == "rejected":
        return {
            "status": normalized,
            "state": "warning",
            "detail": str(error or f"{normalized}"),
        }
    if normalized in done_values:
        return {"status": normalized, "state": "ok", "detail": done_detail}
    if normalized in active_values:
        return {"status": normalized, "state": "active", "detail": active_detail}
    return {"status": normalized, "state": "warning", "detail": empty_detail}


def document_analysis_steps(document: dict[str, Any], chunks: Optional[dict[str, Any]] = None) -> list[dict[str, Any]]:
    chunks = chunks or {}
    parse = _analysis_state(
        document.get("parse_status"),
        done_values={"parsed"},
        active_values={"parsing"},
        empty_detail="尚未解析章节",
        done_detail="章节已解析",
        active_detail="正在解析章节",
        error=document.get("parse_error"),
    )
    index_status = chunks.get("index_status") or document.get("index_status")
    index = _analysis_state(
        index_status,
        done_values={"indexed"},
        active_values={"indexing"},
        empty_detail="尚未建立可问答索引",
        done_detail="已写入知识库",
        active_detail="正在写入知识库",
        error=chunks.get("index_error") or document.get("index_error"),
    )
    chemistry = _analysis_state(
        document.get("chemistry_status"),
        done_values={"extracted"},
        active_values={"extracting"},
        empty_detail="尚未抽取反应集",
        done_detail="反应集已抽取",
        active_detail="正在抽取反应集",
        error=document.get("chemistry_error"),
    )
    translation_state = "neutral" if parse["state"] == "ok" else "warning"
    translation_detail = "解析后可生成或查看翻译" if parse["state"] == "ok" else "需要先解析章节"
    return [
        {"key": "parse", "label": "解析章节", **parse},
        {"key": "index", "label": "写入知识库", **index},
        {
            "key": "translation",
            "label": "翻译预览",
            "status": "available_after_parse" if parse["state"] == "ok" else "blocked_until_parse",
            "state": translation_state,
            "detail": translation_detail,
        },
        {"key": "chemistry", "label": "沉淀化学库", **chemistry},
    ]
```

- [ ] **Step 7: Append failing test for chemistry deposition summary**

Add this test to the end of `tests/test_frontend_api.py`:

```python
def test_chemistry_deposition_summary_counts_review_state():
    from app import frontend_api

    summary = frontend_api.chemistry_deposition_summary(
        {
            "id": 4,
            "document_id": 2,
            "status": "pending",
            "name": "Extracted reaction set",
            "gas_mixture": "O2 / Ar",
            "lxcat_db": "Biagi",
            "reactions": [
                {"id": 1, "verified": True},
                {"id": 2, "verified": False},
            ],
        }
    )

    assert summary == {
        "reaction_set_id": 4,
        "document_id": 2,
        "title": "Extracted reaction set",
        "status": "pending",
        "reaction_count": 2,
        "verified_count": 1,
        "unverified_count": 1,
        "export_ready": False,
        "gas_mixture": "O2 / Ar",
        "lxcat_db": "Biagi",
        "summary": "反应集 #4 · 2 条反应 · 1 条待复核 · O2 / Ar · LXCat: Biagi",
    }
```

- [ ] **Step 8: Run test to verify it fails**

Run:

```bash
python -m pytest tests/test_frontend_api.py::test_chemistry_deposition_summary_counts_review_state -q
```

Expected: fail with `AttributeError: module 'app.frontend_api' has no attribute 'chemistry_deposition_summary'`.

- [ ] **Step 9: Implement chemistry deposition summary helper**

Add this code to `app/frontend_api.py` after `document_analysis_steps()`:

```python
def chemistry_deposition_summary(detail: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {
            "reaction_set_id": None,
            "document_id": None,
            "title": "Reaction set",
            "status": "invalid",
            "reaction_count": 0,
            "verified_count": 0,
            "unverified_count": 0,
            "export_ready": False,
            "gas_mixture": "-",
            "lxcat_db": "-",
            "summary": "反应集无效",
        }
    review_state = reaction_set_review_state(detail)
    reaction_set_id = detail.get("id")
    document_id = detail.get("document_id")
    title = detail.get("name") if isinstance(detail.get("name"), str) and detail.get("name").strip() else "Reaction set"
    status = detail.get("status") if isinstance(detail.get("status"), str) and detail.get("status").strip() else "unknown"
    gas_mixture = detail.get("gas_mixture") if isinstance(detail.get("gas_mixture"), str) and detail.get("gas_mixture").strip() else "-"
    lxcat_db = detail.get("lxcat_db") if isinstance(detail.get("lxcat_db"), str) and detail.get("lxcat_db").strip() else "-"
    reaction_count = review_state["reaction_count"]
    unverified_count = len(review_state["unverified_reactions"])
    verified_count = max(reaction_count - unverified_count, 0)
    export_ready = reaction_count > 0 and unverified_count == 0 and status == "verified"
    summary_parts = [
        f"反应集 #{reaction_set_id if reaction_set_id is not None else '-'}",
        f"{reaction_count} 条反应",
        f"{unverified_count} 条待复核",
    ]
    if gas_mixture != "-":
        summary_parts.append(gas_mixture)
    if lxcat_db != "-":
        summary_parts.append(f"LXCat: {lxcat_db}")
    return {
        "reaction_set_id": reaction_set_id,
        "document_id": document_id,
        "title": title,
        "status": status,
        "reaction_count": reaction_count,
        "verified_count": verified_count,
        "unverified_count": unverified_count,
        "export_ready": export_ready,
        "gas_mixture": gas_mixture,
        "lxcat_db": lxcat_db,
        "summary": " · ".join(summary_parts),
    }
```

- [ ] **Step 10: Run helper tests**

Run:

```bash
python -m pytest tests/test_frontend_api.py -q
```

Expected: all tests in `tests/test_frontend_api.py` pass.

- [ ] **Step 11: Commit helper changes**

Run:

```bash
git add app/frontend_api.py tests/test_frontend_api.py
git commit -m "feat: add workbench frontend state helpers"
```

Expected: commit succeeds.

---

### Task 2: Refactor Streamlit Into Render Functions Without Changing Main Behavior

**Files:**
- Modify: `streamlit_app.py`

**Interfaces:**
- Consumes: existing `api_get()`, `api_post()`, `api_put()`, `api_delete()` wrappers and all imported helpers.
- Produces:
  - `load_health_or_stop() -> dict`
  - `load_status_or_stop(*, check_external: bool = False) -> dict`
  - `render_paper_search_panel(journals: list[dict[str, Any]], categories: list[dict[str, Any]]) -> None`
  - `render_config_panel() -> None`
  - `render_documents_panel() -> Optional[dict[str, Any]]`
  - `render_rag_panel(selected_document: Optional[dict[str, Any]] = None) -> None`
  - `render_chemistry_panel(selected_document: Optional[dict[str, Any]] = None) -> None`
  - `render_system_maintenance(status: dict) -> None`

- [ ] **Step 1: Create a safety checkpoint**

Run:

```bash
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py -q
```

Expected: both commands pass before refactoring.

- [ ] **Step 2: Add typing imports and load helpers**

Modify the import block at the top of `streamlit_app.py`:

```python
import os
from typing import Any, Optional

import streamlit as st
```

Add these functions immediately after `api_delete()`:

```python
def load_health_or_stop() -> dict[str, Any]:
    try:
        health = api_get("/health")
        health_display = health_display_state(health)
        if health_display["warning"]:
            st.warning(health_display["warning"])
        return health
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        with st.expander("Raw API response"):
            st.json(exc.payload)
        st.stop()


def load_status_or_stop(*, check_external: bool = False) -> dict[str, Any]:
    try:
        return api_get("/system/status", check_external=True) if check_external else api_get("/system/status")
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        with st.expander("Raw API response"):
            st.json(exc.payload)
        st.stop()
```

- [ ] **Step 3: Extract the current sidebar into `render_system_maintenance()`**

Cut the current `with st.sidebar:` block from `streamlit_app.py`. Paste its body into this function, replacing the first status load block with the passed `status` parameter:

```python
def render_system_maintenance(status: dict[str, Any]) -> None:
    st.subheader("系统")
    if st.button("检查 GROBID", key="maintenance-check-grobid"):
        status = load_status_or_stop(check_external=True)
    for row in system_count_metric_rows(status.get("counts")):
        st.metric(row["label"], row["value"])
        if row.get("warning"):
            st.warning(row["warning"])
    release_readiness = status.get("release_readiness") or {}
    st.subheader("发布就绪")
    release_display = release_readiness_display_state(release_readiness)
    blockers = release_display["blockers"]
    release_ready = release_display["ready"]
    if release_ready:
        st.success("release ready")
    else:
        blocker_label = ", ".join(blockers) if blockers else "unknown"
        st.warning(f"release blockers: {blocker_label}")
        st.caption("release blocker details")
        for group in release_display["groups"]:
            if group["items"]:
                st.caption(f"{group['label']} {', '.join(group['items'])}")
    demo_data = status.get("demo_data") or {}
    st.subheader("演示数据")
    demo_display = demo_data_display_state(demo_data)
    if demo_display["ready"]:
        st.success("walking skeleton ready")
    else:
        missing_demo_data = demo_display["missing"]
        missing_label = ", ".join(missing_demo_data) if missing_demo_data else "unknown"
        st.warning(f"walking skeleton missing: {missing_label}")
        st.caption("run: python scripts/prepare_demo_data.py")
    runtime_rows = runtime_status_rows(status.get("runtime"))
    for row in runtime_rows:
        if row["kind"] == "warning":
            st.warning(row["text"])
        else:
            st.caption(row["text"])
    st.subheader("API 文档")
    for label, url in api_docs_links(API_BASE).items():
        st.link_button(label, url)
    database_path_row = database_path_status_row(status.get("database_path"))
    if database_path_row["kind"] == "warning":
        st.warning(database_path_row["text"])
    else:
        st.caption(database_path_row["text"])
    external_capabilities = status.get("external_capabilities", {})
    external_display = external_capabilities_display_state(external_capabilities)
    external_capabilities = external_display["capabilities"]
    st.subheader("外部能力")
    for warning in external_display["warnings"]:
        st.warning(warning)
    st.caption(f"OpenAlex mailto: {'已配置' if external_capabilities.get('openalex_mailto') else '未配置'}")
    st.caption(f"Unpaywall email: {'已配置' if external_capabilities.get('unpaywall_email') else '未配置'}")
    st.caption(f"GROBID URL: {external_capabilities.get('grobid_url') or '-'}")
    st.caption(f"LLM key: {'已配置' if external_capabilities.get('llm_api_key') else '未配置'}")
    st.caption(f"Translation adapter: {external_capabilities.get('translation_adapter') or '-'}")
    st.caption(f"LLM model: {external_capabilities.get('llm_model') or '-'}")
    st.caption(f"Embedding: {external_capabilities.get('embedding_model') or '-'}")
    st.caption(f"Vector DB: {external_capabilities.get('vector_db_backend') or '-'}")
    grobid = external_display["grobid"]
    grobid_available = grobid.get("available")
    if grobid_available is True:
        grobid_live = "可用"
    elif grobid_available is False:
        grobid_live = "不可用"
    else:
        grobid_live = "未检查"
    st.caption(f"GROBID live: {grobid_live}")
    if grobid.get("status_code") is not None:
        st.caption(f"GROBID status_code: {grobid.get('status_code')}")
    if grobid.get("error"):
        st.warning(f"GROBID error: {grobid.get('error')}")
    storage_health = status.get("storage_health", {})
    if storage_health:
        st.subheader("存储健康")
        for row in storage_health_caption_rows(storage_health):
            if row["kind"] == "warning":
                st.warning(row["text"])
            else:
                st.caption(row["text"])
    status_counts = status.get("status_counts", {})
    if status_counts:
        st.subheader("状态分布")
        workflow_status_count_rows = status_count_rows(status_counts)
        if workflow_status_count_rows:
            st.dataframe(workflow_status_count_rows, use_container_width=True)
            failed_workflow_rows = [row for row in workflow_status_count_rows if row["status"] == "failed" and row["count"]]
            if failed_workflow_rows:
                failed_summary = ", ".join(
                    f"{row['workflow']}={row['count']}" for row in failed_workflow_rows
                )
                st.warning(f"failed workflow backlog: {failed_summary}")
    config_warnings = status.get("config_warnings") or []
    if config_warnings:
        st.subheader("配置提示")
        warning_rows = config_warning_rows(config_warnings)
        for warning in warning_rows:
            st.warning(f"{warning['capability']}: {warning['message']}")
```

This function body is intentionally the same content as the old sidebar. The only behavior change is that it renders where called.

- [ ] **Step 4: Extract tab bodies into render functions**

Move the body of each current tab into a named function. Keep the code inside each function unchanged except for indentation and any calls needed to pass `selected_document`.

Use these function declarations:

```python
def render_paper_search_panel() -> None:
    st.caption("可先运行 `python scripts/import_fixtures.py` 导入离线样例。")
```

Paste the current `with search_tab:` body after the caption line, excluding the tab wrapper line.

```python
def render_config_panel() -> None:
    config_journals_page_col, config_journals_page_size_col = st.columns(2)
```

Paste the current `with config_tab:` body after the first line, excluding the tab wrapper line.

```python
def render_documents_panel() -> Optional[dict[str, Any]]:
    selected_document_detail: Optional[dict[str, Any]] = None
```

Paste the current `with documents_tab:` body after the first line, excluding the tab wrapper line. After the existing successful `document_detail = api_get(f"/documents/{selected['id']}")` call, add:

```python
        selected_document_detail = document_detail
```

At the end of the function, add:

```python
    return selected_document_detail
```

```python
def render_rag_panel(selected_document: Optional[dict[str, Any]] = None) -> None:
    rag_documents_page_col, rag_documents_page_size_col = st.columns(2)
```

Paste the current `with rag_tab:` body after the first line, excluding the tab wrapper line. Do not change RAG behavior in this task.

```python
def render_chemistry_panel(selected_document: Optional[dict[str, Any]] = None) -> None:
    chemistry_documents_page_col, chemistry_documents_page_size_col = st.columns(2)
```

Paste the current `with chemistry_tab:` body after the first line, excluding the tab wrapper line. Do not change chemistry behavior in this task.

- [ ] **Step 5: Recreate old tabs with render functions**

Replace the old top-level tab composition with:

```python
st.set_page_config(page_title="paper-lab-agent", layout="wide")
st.title("paper-lab-agent")

health = load_health_or_stop()
health_display = health_display_state(health)
st.caption(health_display["caption"])

review_message = st.session_state.pop("reaction_review_message", None)
if review_message:
    st.success(review_message)

status = load_status_or_stop()

search_tab, config_tab, documents_tab, rag_tab, chemistry_tab = st.tabs(["检索", "配置", "文档", "问答", "化学库"])

with search_tab:
    render_paper_search_panel()
with config_tab:
    render_config_panel()
with documents_tab:
    selected_document = render_documents_panel()
with rag_tab:
    render_rag_panel(selected_document=None)
with chemistry_tab:
    render_chemistry_panel(selected_document=None)

with st.expander("System and maintenance", expanded=False):
    render_system_maintenance(status)
```

- [ ] **Step 6: Verify the mechanical refactor**

Run:

```bash
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py -q
DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh
```

Expected:

- `py_compile` passes.
- `tests/test_frontend_api.py` passes.
- `./start.sh` exits after both API and Streamlit are ready.

- [ ] **Step 7: Commit mechanical refactor**

Run:

```bash
git add streamlit_app.py
git commit -m "refactor: split streamlit panels into render functions"
```

Expected: commit succeeds.

---

### Task 3: Compose the Three-Column Research Workbench

**Files:**
- Modify: `streamlit_app.py`

**Interfaces:**
- Consumes:
  - `workbench_status_cards(status)`
  - render functions from Task 2.
- Produces:
  - `render_status_strip(status: dict[str, Any]) -> None`
  - `render_library_intake_column() -> Optional[dict[str, Any]]`
  - `render_knowledge_column(selected_document: Optional[dict[str, Any]]) -> None`
  - `render_chemistry_column(selected_document: Optional[dict[str, Any]]) -> None`

- [ ] **Step 1: Import new helper functions**

Add these names to the existing `from app.frontend_api import (` import list in `streamlit_app.py`:

```python
    chemistry_deposition_summary,
    document_analysis_steps,
    rag_document_ids_for_scope,
    workbench_status_cards,
```

- [ ] **Step 2: Add `render_status_strip()`**

Add this function after `load_status_or_stop()`:

```python
def render_status_strip(status: dict[str, Any]) -> None:
    cards = workbench_status_cards(status)
    if not cards:
        st.warning("workbench status unavailable")
        return
    columns = st.columns(min(len(cards), 6))
    for index, card in enumerate(cards):
        column = columns[index % len(columns)]
        state = card.get("state")
        label = f"{card.get('group')} · {card.get('label')}"
        value = card.get("value")
        detail = card.get("detail")
        column.metric(label, value)
        if state == "warning":
            column.caption(f"需关注: {detail}")
        elif state == "active":
            column.caption(f"进行中: {detail}")
        else:
            column.caption(str(detail or ""))
```

- [ ] **Step 3: Add three workbench column wrappers**

Add these functions after `render_system_maintenance()`:

```python
def render_library_intake_column() -> Optional[dict[str, Any]]:
    st.subheader("资料库")
    with st.expander("论文检索与抓取", expanded=True):
        render_paper_search_panel()
    with st.expander("PDF 队列与入库", expanded=True):
        return render_documents_panel()


def render_knowledge_column(selected_document: Optional[dict[str, Any]]) -> None:
    st.subheader("知识库问答")
    render_rag_panel(selected_document=selected_document)
    st.divider()
    st.subheader("文章分析")
    if selected_document is None:
        st.info("从左侧选择一个 PDF 后，这里会显示章节、翻译、索引和化学抽取状态。")
        return
    st.caption(document_option_label(selected_document))
    st.dataframe(document_status_rows(selected_document), use_container_width=True)


def render_chemistry_column(selected_document: Optional[dict[str, Any]]) -> None:
    st.subheader("化学库沉淀")
    if selected_document is None:
        st.info("从左侧选择 PDF 后，这里会显示该文档沉淀出的反应集。")
    render_chemistry_panel(selected_document=selected_document)
```

This keeps existing detailed document and chemistry behavior available while the next task tightens defaults and selected-document coupling.

- [ ] **Step 4: Replace tab composition with three columns**

Replace the tab block from Task 2 with:

```python
st.set_page_config(page_title="paper-lab-agent", layout="wide")
st.title("paper-lab-agent")

health = load_health_or_stop()
health_display = health_display_state(health)
st.caption(f"{health_display['caption']} · 三栏研究工作台")

review_message = st.session_state.pop("reaction_review_message", None)
if review_message:
    st.success(review_message)

status = load_status_or_stop()
render_status_strip(status)

left_col, middle_col, right_col = st.columns([0.28, 0.44, 0.28], gap="large")
with left_col:
    selected_document = render_library_intake_column()
with middle_col:
    render_knowledge_column(selected_document)
with right_col:
    render_chemistry_column(selected_document)

with st.expander("System and maintenance", expanded=False):
    maintenance_tab, config_tab = st.tabs(["系统状态", "配置维护"])
    with maintenance_tab:
        render_system_maintenance(status)
    with config_tab:
        render_config_panel()
```

- [ ] **Step 5: Verify first workbench composition**

Run:

```bash
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py -q
DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh
python scripts/health_check.py --require-frontend
```

Expected:

- Streamlit starts successfully.
- Frontend health check passes.
- The first screen no longer shows the old module tabs.

- [ ] **Step 6: Commit workbench shell**

Run:

```bash
git add streamlit_app.py
git commit -m "feat: compose streamlit research workbench"
```

Expected: commit succeeds.

---

### Task 4: Make Q&A Knowledge-Base First and Group PDF Analysis Controls

**Files:**
- Modify: `streamlit_app.py`

**Interfaces:**
- Consumes:
  - `rag_document_ids_for_scope(scope, selected_document_ids, typed_document_ids)`
  - `document_analysis_steps(document, chunks)`
  - existing `/rag/query`, `/documents/{id}/parse`, `/translate`, `/index`, `/extract-chemistry`.
- Produces:
  - RAG panel defaults to whole knowledge base.
  - Selected document is an optional scope.
  - PDF analysis controls are grouped together in the middle column.

- [ ] **Step 1: Update `render_rag_panel()` scope controls**

Inside `render_rag_panel()`, replace the current `doc_ids = st.text_input("document_ids", value="")` block through the existing `ids = list(dict.fromkeys(selected_document_ids + typed_document_ids))` construction with:

```python
    scope_options = ["全部知识库", "选中文档", "手动范围"]
    scope = st.radio(
        "问答范围",
        scope_options,
        horizontal=True,
        key="rag-scope",
        help="默认查询整个已索引知识库；只有明确选择时才限定文档。",
    )
    selected_document_ids = []
    if selected_document is not None and isinstance(selected_document.get("id"), int):
        selected_document_ids = [int(selected_document["id"])]
        st.caption(f"当前阅读上下文: document #{selected_document['id']}")
    doc_ids = st.text_input("手动 document_ids", value="", help="仅在选择手动范围或选中文档时追加使用。")
```

Then replace the current typed id parsing inside the submit block with:

```python
            typed_document_ids = [int(part.strip()) for part in doc_ids.split(",") if part.strip()]
            ids = rag_document_ids_for_scope(scope, selected_document_ids, typed_document_ids)
            document_id_error = None
```

Keep the existing `ValueError` handling and `/rag/query` call.

- [ ] **Step 2: Add article analysis controls to `render_knowledge_column()`**

Replace the body after `st.caption(document_option_label(selected_document))` in `render_knowledge_column()` with:

```python
    try:
        document_detail = api_get(f"/documents/{selected_document['id']}")
    except FrontendApiError as exc:
        st.warning(format_error_payload(exc.payload, exc.status_code))
        with st.expander("Raw API response"):
            st.json(exc.payload)
        return

    try:
        chunks = api_get(f"/documents/{selected_document['id']}/chunks", page=1, page_size=20)
        chunks = document_chunks_response_state(chunks)
    except FrontendApiError as exc:
        chunks = {"items": [], "total": 0, "page": 1, "page_size": 20, "indexed": False, "index_status": "not_indexed", "index_error": format_error_payload(exc.payload, exc.status_code)}

    st.dataframe(document_analysis_steps(document_detail, chunks), use_container_width=True)
    analysis_cols = st.columns(4)
    if analysis_cols[0].button("解析章节", key=f"analysis-parse-{selected_document['id']}"):
        status_code, parse_payload = api_post(f"/documents/{selected_document['id']}/parse")
        if status_code < 400:
            st.success("已创建解析任务")
        else:
            st.warning(format_error_payload(parse_payload, status_code))
        with st.expander("Raw API response"):
            st.json(parse_payload)
    translation_target_lang = analysis_cols[1].text_input("翻译目标", value="zh", key=f"analysis-translation-target-{selected_document['id']}")
    if analysis_cols[1].button("生成翻译", key=f"analysis-translate-{selected_document['id']}"):
        status_code, translate_payload = api_post(
            f"/documents/{selected_document['id']}/translate",
            json={"target_lang": translation_target_lang},
        )
        if status_code < 400:
            st.success("已创建翻译任务")
        else:
            st.warning(format_error_payload(translate_payload, status_code))
        with st.expander("Raw API response"):
            st.json(translate_payload)
    if analysis_cols[2].button("写入知识库", key=f"analysis-index-{selected_document['id']}"):
        status_code, index_payload = api_post(f"/documents/{selected_document['id']}/index")
        if status_code < 400:
            st.success("已创建索引任务")
        else:
            st.warning(format_error_payload(index_payload, status_code))
        with st.expander("Raw API response"):
            st.json(index_payload)
    if analysis_cols[3].button("沉淀化学库", key=f"analysis-chemistry-{selected_document['id']}"):
        status_code, extract_payload = api_post(f"/documents/{selected_document['id']}/extract-chemistry")
        if status_code < 400:
            st.success("已创建化学抽取任务")
        else:
            st.warning(format_error_payload(extract_payload, status_code))
        with st.expander("Raw API response"):
            st.json(extract_payload)
```

After this block, keep section, translation, and chunk previews by moving the existing preview logic from `render_documents_panel()` into `render_knowledge_column()` only if doing so does not duplicate widgets. If duplication appears, remove the previews from `render_documents_panel()` and keep them in `render_knowledge_column()`.

- [ ] **Step 3: Simplify `render_documents_panel()` to intake and queue**

In `render_documents_panel()`, keep:

- PDF upload.
- Associated paper search.
- document page/page_size controls.
- status filter.
- document selectbox.
- document detail fetch that sets `selected_document_detail`.

Remove from `render_documents_panel()`:

- parse/translate/index/extract buttons.
- section preview.
- translation preview.
- chunk preview.

Those controls now belong to `render_knowledge_column()`.

- [ ] **Step 4: Verify knowledge-base default behavior**

Run:

```bash
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py::test_rag_document_ids_for_scope_defaults_to_whole_knowledge_base -q
DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh
python scripts/health_check.py --require-frontend
```

Expected:

- Helper test passes.
- Streamlit starts.
- RAG default scope is "全部知识库".

- [ ] **Step 5: Commit Q&A and PDF analysis changes**

Run:

```bash
git add streamlit_app.py
git commit -m "feat: make workbench qa knowledge-base first"
```

Expected: commit succeeds.

---

### Task 5: Tighten Chemistry Delivery Around Deposition, Review, and Export

**Files:**
- Modify: `streamlit_app.py`

**Interfaces:**
- Consumes:
  - `chemistry_deposition_summary(detail)`
  - existing `reaction_set_review_state()`, `reaction_review_rows()`, `reaction_review_form_state()`, `reaction_review_payload()`, `reaction_export_success_state()`, `reaction_export_download()`.
- Produces:
  - Right column frames reaction sets as PDF analysis output.
  - Selected document drives default reaction-set loading.
  - Pending reactions appear before already verified reactions.

- [ ] **Step 1: Update selected-document default in `render_chemistry_panel()`**

At the beginning of `render_chemistry_panel()`, before document selectors, add:

```python
    selected_document_id = None
    if selected_document is not None and isinstance(selected_document.get("id"), int):
        selected_document_id = int(selected_document["id"])
        st.caption(f"当前 PDF 沉淀: document #{selected_document_id}")
```

When setting `chemistry_document_id`, prefer `selected_document_id`:

```python
    if selected_document_id is not None:
        chemistry_document_id = selected_document_id
    elif not chemistry_documents:
        st.info("暂无可选文档，请先上传并抽取化学库。")
        chemistry_document_id = st.number_input("手动 document_id", min_value=1, value=1)
    elif not filtered_chemistry_documents:
        st.info("当前页没有匹配筛选状态的化学库文档。")
        chemistry_document_id = st.number_input("手动 document_id", min_value=1, value=1)
    else:
        chemistry_document_options = filtered_chemistry_documents
        selected_chemistry_document = st.selectbox(
            "化学库文档",
            chemistry_document_options,
            format_func=document_option_label,
            key="chemistry-document-select",
        )
        chemistry_document_id = int(selected_chemistry_document["id"])
        st.caption(f"chemistry_document_id: {chemistry_document_id}")
```

- [ ] **Step 2: Auto-load reaction sets for selected document**

After `chemistry_document_id` is assigned, add:

```python
    if selected_document_id is not None and st.session_state.get("loaded_chemistry_document_id") != selected_document_id:
        try:
            st.session_state["document_reaction_sets"] = api_get(
                f"/documents/{selected_document_id}/reaction-sets",
                page=1,
                page_size=20,
            )
            st.session_state["loaded_chemistry_document_id"] = selected_document_id
        except FrontendApiError as exc:
            st.warning(format_error_payload(exc.payload, exc.status_code))
            with st.expander("Raw API response"):
                st.json(exc.payload)
            st.session_state["document_reaction_sets"] = None
```

Keep the manual "加载文档反应集" button for cases without selected document.

- [ ] **Step 3: Add deposition summary above reaction review**

Inside `if detail:`, immediately after `review_state = reaction_set_review_state(detail)`, add:

```python
        deposition = chemistry_deposition_summary(detail)
        st.caption(deposition["summary"])
        d1, d2, d3 = st.columns(3)
        d1.metric("反应", deposition["reaction_count"])
        d2.metric("已复核", deposition["verified_count"])
        d3.metric("待复核", deposition["unverified_count"])
        if deposition["export_ready"]:
            st.success("该反应集已通过复核，可以导出。")
        else:
            st.info("化学库已沉淀，完成复核后才能导出。")
```

- [ ] **Step 4: Keep pending reactions first**

Replace:

```python
        display_reactions = review_list_state["display_reactions"]
```

with:

```python
        display_reactions = sorted(
            review_list_state["display_reactions"],
            key=lambda item: (bool(item.get("verified")), item.get("id") or 0),
        )
```

- [ ] **Step 5: Verify chemistry flow**

Run:

```bash
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py::test_chemistry_deposition_summary_counts_review_state -q
DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh
python scripts/health_check.py --require-frontend
```

Expected:

- Helper test passes.
- Streamlit starts.
- Right column can load reaction sets for the selected document.

- [ ] **Step 6: Commit chemistry delivery changes**

Run:

```bash
git add streamlit_app.py
git commit -m "feat: surface chemistry deposition in workbench"
```

Expected: commit succeeds.

---

### Task 6: Final Verification and Release Gate

**Files:**
- Modify only if verification reveals a defect in files touched by Tasks 1-5.

**Interfaces:**
- Consumes all work from Tasks 1-5.
- Produces a verified workbench redesign ready for review.

- [ ] **Step 1: Run focused checks**

Run:

```bash
python scripts/validate_docs_links.py
git diff --check
git diff --cached --check
python -m py_compile streamlit_app.py
python -m pytest tests/test_frontend_api.py -q
python -m pytest tests/test_api.py -q
DEV_EXIT_AFTER_READY=true START_OPEN_BROWSER=false ./start.sh
python scripts/health_check.py --require-frontend
```

Expected:

- All commands pass.
- `./start.sh` exits cleanly after frontend and backend are ready.

- [ ] **Step 2: Run full release gate**

Run:

```bash
bash scripts/release_check.sh
```

Expected: the release gate passes. Record the final passed test count in the implementation summary.

- [ ] **Step 3: Inspect git state**

Run:

```bash
git branch --show-current
git rev-parse --show-toplevel
git status --short
```

Expected:

- Branch is `phase/5-experiment-lab-artifacts`.
- Worktree root is `/Users/zenith/Desktop/paper-lab-agent`.
- `git status --short` is empty after all task commits.

- [ ] **Step 4: Report manual UI verification status**

Open the Streamlit app started by `./start.sh` if a live browser check is part of the implementation turn. Confirm these visible states:

- First screen is a three-column workbench.
- Top status strip is visible.
- Left column contains paper search, PDF upload, and document queue.
- Middle column says "知识库问答" and default scope is "全部知识库".
- Selected document shows PDF analysis controls: parse, translation, index, chemistry extraction.
- Right column says "化学库沉淀" and shows reaction-set review/export when data exists.
- "System and maintenance" contains system status, release readiness, API docs, and config maintenance.

If browser verification cannot run, say exactly which command or environment condition blocked it.
