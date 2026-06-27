import json
import os

import streamlit as st

from app.frontend_api import (
    FrontendApiError,
    api_docs_links,
    category_parent_option_label,
    crawl_job_diagnostic_rows,
    crawl_job_option_label,
    crawl_job_rows,
    crawl_journal_option_label,
    crawl_journal_options,
    document_asset_downloads,
    document_chunk_rows,
    document_chunk_option_label,
    document_option_label,
    document_section_option_label,
    document_section_rows,
    document_status_rows,
    format_error_payload,
    journal_option_label,
    paper_category_option_label,
    rag_source_option_label,
    rag_source_rows,
    reaction_audit_rows,
    reaction_display_state,
    reaction_export_download,
    reaction_export_rows,
    reaction_review_form_state,
    reaction_review_payload,
    reaction_review_rows,
    reaction_set_option_label,
    reaction_set_review_state,
    reaction_set_rows,
    request_json,
    request_json_status,
    translation_download,
    translation_status_rows,
)


API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")


def api_get(path: str, **params):
    return request_json("GET", API_BASE, path, params=params, timeout=20)


def api_post(path: str, json=None, files=None, data=None):
    return request_json_status("POST", API_BASE, path, json=json, files=files, data=data, timeout=60)


def api_put(path: str, json=None):
    return request_json_status("PUT", API_BASE, path, json=json, timeout=20)


def api_delete(path: str):
    return request_json_status("DELETE", API_BASE, path, timeout=20)


def format_category_summary(paper: dict) -> str:
    details = paper.get("category_details") or []
    if details:
        labels = []
        for category in details:
            confidence = category.get("confidence")
            confidence_label = "-" if confidence is None else f"{confidence:.2f}"
            labels.append(f"{category.get('slug')} · {category.get('method') or '-'} · {confidence_label}")
        return ", ".join(labels)
    return ", ".join(paper.get("categories") or []) or "-"


st.set_page_config(page_title="paper-lab-agent", layout="wide")
st.title("paper-lab-agent")

try:
    health = api_get("/health")
    st.caption(f"{health['service']} · {health['status']}")
except FrontendApiError as exc:
    st.error(format_error_payload(exc.payload, exc.status_code))
    st.json(exc.payload)
    st.stop()

review_message = st.session_state.pop("reaction_review_message", None)
if review_message:
    st.success(review_message)

search_tab, config_tab, documents_tab, rag_tab, chemistry_tab = st.tabs(["检索", "配置", "文档", "问答", "化学库"])

with st.sidebar:
    st.subheader("系统")
    try:
        status = api_get("/system/status")
        if st.button("检查 GROBID"):
            status = api_get("/system/status", check_external=True)
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    st.metric("期刊", status["counts"]["journals"])
    st.metric("论文", status["counts"]["papers"])
    st.metric("文档", status["counts"]["documents"])
    release_readiness = status.get("release_readiness") or {}
    st.subheader("发布就绪")
    RELEASE_BLOCKING_CONFIG_WARNING_CODES = {"unsupported_embedding_model", "unsupported_vector_db_backend"}
    config_warning_codes = [
        str(code) for code in release_readiness.get("config_warning_codes") or [] if str(code).strip()
    ]
    blocking_config_warnings = [
        code for code in config_warning_codes if code in RELEASE_BLOCKING_CONFIG_WARNING_CODES
    ]
    blockers = []
    blocker_groups = {
        "demo_data_missing": "demo data missing:",
        "failed_workflows": "failed workflows:",
        "blocking_config_warnings": "config warnings:",
        "storage_errors": "storage errors:",
    }
    for key in blocker_groups:
        if key == "blocking_config_warnings":
            blockers.extend(f"config_warning_codes:{code}" for code in blocking_config_warnings)
        else:
            blockers.extend(str(item) for item in release_readiness.get(key) or [] if str(item).strip())
    release_ready = release_readiness.get("ready") is True and not blockers
    if release_ready:
        st.success("release ready")
    else:
        blocker_label = ", ".join(blockers) if blockers else "unknown"
        st.warning(f"release blockers: {blocker_label}")
        st.caption("release blocker details")
        for key, label in blocker_groups.items():
            if key == "blocking_config_warnings":
                items = [f"config_warning_codes:{code}" for code in blocking_config_warnings]
            else:
                items = [str(item) for item in release_readiness.get(key) or [] if str(item).strip()]
            if items:
                st.caption(f"{label} {', '.join(items)}")
    demo_data = status.get("demo_data") or {}
    st.subheader("演示数据")
    if demo_data.get("ready"):
        st.success("walking skeleton ready")
    else:
        missing_demo_data = demo_data.get("missing") or []
        missing_label = ", ".join(missing_demo_data) if missing_demo_data else "unknown"
        st.warning(f"walking skeleton missing: {missing_label}")
        st.caption("run: python scripts/prepare_demo_data.py")
    runtime = status.get("runtime", {})
    st.caption(f"API: {runtime.get('api_prefix', '/api/v1')}")
    st.caption(f"version: {runtime.get('version') or '-'}")
    st.subheader("API 文档")
    for label, url in api_docs_links(API_BASE).items():
        st.link_button(label, url)
    st.caption(f"scheduler_enabled: {runtime.get('scheduler_enabled', False)}")
    scheduler_jobs = runtime.get("scheduler_jobs") or []
    if scheduler_jobs:
        st.caption("scheduler_jobs:")
        for job in scheduler_jobs:
            st.caption(f"- {job.get('period')} · {job.get('id')} · {job.get('schedule')} {job.get('timezone')}")
    st.caption(f"DB: {status['database_path']}")
    external_capabilities = status.get("external_capabilities", {})
    st.subheader("外部能力")
    st.caption(f"OpenAlex mailto: {'已配置' if external_capabilities.get('openalex_mailto') else '未配置'}")
    st.caption(f"Unpaywall email: {'已配置' if external_capabilities.get('unpaywall_email') else '未配置'}")
    st.caption(f"GROBID URL: {external_capabilities.get('grobid_url') or '-'}")
    st.caption(f"LLM key: {'已配置' if external_capabilities.get('llm_api_key') else '未配置'}")
    st.caption(f"Translation adapter: {external_capabilities.get('translation_adapter') or '-'}")
    st.caption(f"LLM model: {external_capabilities.get('llm_model') or '-'}")
    st.caption(f"Embedding: {external_capabilities.get('embedding_model') or '-'}")
    st.caption(f"Vector DB: {external_capabilities.get('vector_db_backend') or '-'}")
    grobid = external_capabilities.get("grobid") or {}
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
        for key in ["data_dir", "pdf_dir", "tei_dir", "translation_dir", "export_dir", "database", "vector_db"]:
            health_entry = storage_health.get(key) or {}
            exists_label = "exists" if health_entry.get("exists") else "missing"
            writable_label = "writable" if health_entry.get("writable") else "not writable"
            st.caption(f"{key}: {exists_label} · {writable_label} · {health_entry.get('path') or '-'}")
            if key == "vector_db":
                valid_json = health_entry.get("valid_json")
                valid_json_label = "unchecked" if valid_json is None else ("valid_json" if valid_json else "invalid_json")
                st.caption(f"vector_db valid_json: {valid_json_label}")
            if health_entry.get("error"):
                st.warning(f"{key} error: {health_entry['error']}")
    status_counts = status.get("status_counts", {})
    if status_counts:
        st.subheader("状态分布")
        status_count_rows = [
            {"workflow": workflow, "status": state, "count": count}
            for workflow in ["crawl_jobs", "document_parse", "document_index", "document_chemistry", "translations", "reaction_sets"]
            for state, count in (status_counts.get(workflow) or {}).items()
        ]
        if status_count_rows:
            st.dataframe(status_count_rows, use_container_width=True)
            failed_workflow_rows = [row for row in status_count_rows if row["status"] == "failed" and row["count"]]
            if failed_workflow_rows:
                failed_summary = ", ".join(
                    f"{row['workflow']}={row['count']}" for row in failed_workflow_rows
                )
                st.warning(f"failed workflow backlog: {failed_summary}")
    config_warnings = status.get("config_warnings") or []
    if config_warnings:
        st.subheader("配置提示")
        for warning in config_warnings:
            capability = warning.get("capability") or "unknown"
            message = warning.get("message") or warning.get("code") or "configuration warning"
            st.warning(f"{capability}: {message}")

with search_tab:
    st.caption("可先运行 `python scripts/import_fixtures.py` 导入离线样例。")
    try:
        journals = api_get("/journals", active=True, page_size=100)["items"]
        categories = api_get("/categories")["items"]
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    col1, col2, col3, col4, col5, col6, col7 = st.columns([2, 1, 1, 1, 1, 1, 1])
    q = col1.text_input("关键词", value="plasma")
    journal_names = ["全部"] + [j["name"] for j in journals]
    journal_choice = col2.selectbox("期刊", journal_names)
    category_slugs = ["全部"] + [c["slug"] for c in categories]
    category_choice = col3.selectbox("分类", category_slugs)
    year_from = col4.number_input("year_from", min_value=0, max_value=2100, value=0)
    year_to = col5.number_input("year_to", min_value=0, max_value=2100, value=0)
    oa_only = col6.checkbox("OA only")
    sort_choice = col7.selectbox("排序", ["date_desc", "relevance"])
    page_col, page_size_col = st.columns(2)
    search_page = page_col.number_input("page", min_value=1, value=1, key="search-page")
    search_page_size = page_size_col.number_input("page_size", min_value=1, max_value=100, value=20, key="search-page-size")
    params = {
        "q": q or None,
        "page": int(search_page),
        "page_size": int(search_page_size),
        "oa_only": oa_only,
        "sort": sort_choice,
    }
    if journal_choice != "全部":
        params["journal_id"] = next(j["id"] for j in journals if j["name"] == journal_choice)
    if category_choice != "全部":
        params["category"] = category_choice
    if year_from:
        params["year_from"] = int(year_from)
    if year_to:
        params["year_to"] = int(year_to)
    if year_from and year_to and year_from > year_to:
        st.warning("year_from must be less than or equal to year_to")
        papers = {"items": [], "total": 0, "page": 1, "page_size": 20}
        search_error = None
    elif sort_choice == "relevance" and not q.strip():
        st.warning("sort=relevance requires q")
        papers = {"items": [], "total": 0, "page": 1, "page_size": 20}
        search_error = None
    else:
        try:
            papers = api_get("/papers", **{k: v for k, v in params.items() if v is not None})
            search_error = None
        except FrontendApiError as exc:
            papers = {"items": [], "total": 0, "page": 1, "page_size": 20}
            search_error = exc
            st.caption("检索失败")
            st.warning(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
    st.metric("结果", papers["total"])
    st.caption(f"page {papers['page']} · page_size {papers['page_size']}")
    if not search_error and papers["total"] == 0:
        st.info("没有检索结果。")
    for paper in papers["items"]:
        with st.container(border=True):
            st.subheader(paper["title"])
            st.caption(f"{paper.get('journal_name') or '-'} · {paper.get('published_date') or '-'} · {paper.get('oa_status') or 'unknown'}")
            dedupe_label = paper.get("doi") or (paper.get("dedupe_key") or "")[:24]
            st.caption(
                f"source={paper.get('source_api') or '-'} · "
                f"dedupe_strategy={paper.get('dedupe_strategy') or '-'} · "
                f"has_doi={paper.get('has_doi')} · key={dedupe_label or '-'}"
            )
            st.write((paper.get("abstract") or "")[:400])
            st.caption(f"分类结果: {format_category_summary(paper)}")
            if st.button("触发分类", key=f"classify-paper-{paper['id']}"):
                status_code, classified_paper = api_post(f"/papers/{paper['id']}/classify")
                if status_code < 400:
                    st.success(format_category_summary(classified_paper))
                else:
                    st.warning(format_error_payload(classified_paper, status_code))
                    st.json(classified_paper)
            if st.button(
                "重新解析 OA",
                key=f"resolve-oa-{paper['id']}",
                disabled=not paper.get("doi"),
                help="需要 DOI 才能通过 Unpaywall 解析 OA 链接",
            ):
                status_code, resolved_paper = api_post(f"/papers/{paper['id']}/resolve-oa")
                if status_code < 400:
                    resolved_oa_status = resolved_paper.get("oa_status") or "unknown"
                    resolved_oa_pdf_url = resolved_paper.get("oa_pdf_url") or "-"
                    st.success(f"oa_status={resolved_oa_status} · oa_pdf_url={resolved_oa_pdf_url}")
                else:
                    st.warning(format_error_payload(resolved_paper, status_code))
                    st.json(resolved_paper)
            category_options_by_slug = {category["slug"]: category for category in categories}
            current_category_slugs = set(paper.get("categories") or [])
            default_categories = [
                category_options_by_slug[slug] for slug in current_category_slugs if slug in category_options_by_slug
            ]
            with st.expander("人工覆盖分类"):
                selected_categories = st.multiselect(
                    "人工覆盖分类",
                    categories,
                    default=default_categories,
                    format_func=paper_category_option_label,
                    key=f"manual-categories-{paper['id']}",
                )
                if st.button("保存人工分类", key=f"save-manual-categories-{paper['id']}"):
                    selected_category_ids = [category["id"] for category in selected_categories]
                    status_code, updated_paper = api_put(
                        f"/papers/{paper['id']}/categories",
                        json={"category_ids": selected_category_ids, "method": "manual"},
                    )
                    if status_code < 400:
                        st.success(format_category_summary(updated_paper))
                    else:
                        st.warning(format_error_payload(updated_paper, status_code))
                        st.json(updated_paper)
            links = []
            if paper.get("oa_pdf_url"):
                links.append(f"[OA PDF]({paper['oa_pdf_url']})")
            if paper.get("landing_url"):
                links.append(f"[Landing]({paper['landing_url']})")
            if links:
                st.markdown(" · ".join(links))

    st.divider()
    st.subheader("抓取任务")
    crawl_col1, crawl_col2, crawl_col3 = st.columns([1, 1, 1])
    crawl_journal_choice = crawl_col1.selectbox(
        "抓取期刊",
        crawl_journal_options(journals),
        format_func=crawl_journal_option_label,
    )
    selected_crawl_journal_id = crawl_journal_choice["journal_id"]
    date_from = crawl_col2.text_input("date_from", value="")
    date_to = crawl_col3.text_input("date_to", value="")
    if st.button("创建抓取任务"):
        crawl_date_error = date_from and date_to and date_from > date_to
        if crawl_date_error:
            st.warning("date_from must be less than or equal to date_to")
        else:
            body = {"period": "manual"}
            if selected_crawl_journal_id is not None:
                body["journal_ids"] = [int(selected_crawl_journal_id)]
            if date_from:
                body["date_from"] = date_from
            if date_to:
                body["date_to"] = date_to
            status_code, crawl_payload = api_post("/crawl/run", json=body)
            if status_code < 400:
                st.success("已创建抓取任务")
            else:
                st.warning(format_error_payload(crawl_payload, status_code))
            st.json(crawl_payload)
    crawl_jobs_page_col, crawl_jobs_page_size_col = st.columns(2)
    crawl_jobs_page = crawl_jobs_page_col.number_input("crawl_jobs_page", min_value=1, value=1, key="crawl-jobs-page")
    crawl_jobs_page_size = crawl_jobs_page_size_col.number_input(
        "crawl_jobs_page_size",
        min_value=1,
        max_value=100,
        value=10,
        key="crawl-jobs-page-size",
    )
    try:
        crawl_jobs_response = api_get("/crawl/jobs", page=int(crawl_jobs_page), page_size=int(crawl_jobs_page_size))
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    jobs = crawl_jobs_response["items"]
    st.caption(
        f"crawl jobs page {crawl_jobs_response['page']} · "
        f"page_size {crawl_jobs_response['page_size']} · "
        f"total {crawl_jobs_response['total']}"
    )
    st.dataframe(crawl_job_rows(jobs), use_container_width=True)
    if not jobs:
        st.info("暂无抓取任务。")
    else:
        selected_job = st.selectbox(
            "任务详情",
            jobs,
            format_func=crawl_job_option_label,
        )
        try:
            job_detail = api_get(f"/crawl/jobs/{selected_job['id']}")
        except FrontendApiError as exc:
            job_detail = None
            st.warning(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
        if job_detail:
            diagnostics = job_detail.get("diagnostics", {})
            j1, j2, j3, j4 = st.columns(4)
            j1.metric("found", diagnostics.get("papers_found", 0))
            j2.metric("filtered", diagnostics.get("papers_filtered", 0))
            j3.metric("accepted", diagnostics.get("papers_accepted", 0))
            j4.metric("new", diagnostics.get("papers_new", 0))
            st.caption(f"outcome: {diagnostics.get('outcome') or 'unknown'}")
            if diagnostics.get("error"):
                st.warning(diagnostics["error"])
            st.dataframe(crawl_job_diagnostic_rows(job_detail), use_container_width=True)
            st.json(job_detail)

with config_tab:
    config_journals_page_col, config_journals_page_size_col = st.columns(2)
    config_journals_page = config_journals_page_col.number_input(
        "config_journals_page",
        min_value=1,
        value=1,
        key="config-journals-page",
    )
    config_journals_page_size = config_journals_page_size_col.number_input(
        "config_journals_page_size",
        min_value=1,
        max_value=100,
        value=100,
        key="config-journals-page-size",
    )
    try:
        journals_response = api_get("/journals", page=int(config_journals_page), page_size=int(config_journals_page_size))
        categories_response = api_get("/categories", page=1, page_size=100)
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    journals_all = journals_response["items"]
    categories_all = categories_response["items"]

    st.subheader("期刊白名单")
    st.caption(
        f"journals page {journals_response['page']} · "
        f"page_size {journals_response['page_size']} · "
        f"total {journals_response['total']}"
    )
    journals_table = [
        {
            **journal,
            "keywords": json.dumps(journal.get("keywords"), ensure_ascii=False)
            if isinstance(journal.get("keywords"), (dict, list))
            else journal.get("keywords"),
        }
        for journal in journals_all
    ]
    st.dataframe(journals_table, use_container_width=True)

    with st.form("create-journal-form"):
        st.markdown("新增期刊")
        j1, j2 = st.columns(2)
        journal_name = j1.text_input("name", key="new-journal-name")
        publisher = j2.text_input("publisher", key="new-journal-publisher")
        j3, j4 = st.columns(2)
        issn_print = j3.text_input("issn_print", key="new-journal-issn-print")
        issn_electronic = j4.text_input("issn_electronic", key="new-journal-issn-electronic")
        j5, j6 = st.columns(2)
        year_from = j5.number_input("year_from", min_value=1900, max_value=2100, value=1990, key="new-journal-year-from")
        new_journal_year_to = j6.number_input("year_to", min_value=0, max_value=2100, value=0, key="new-journal-year-to")
        platform = st.text_input("platform", key="new-journal-platform")
        url = st.text_input("url", key="new-journal-url")
        keywords_mode = st.selectbox("keywords_mode", ["or", "and"], key="new-journal-keywords-mode")
        keywords_terms = st.text_area("keywords_terms", key="new-journal-keywords-terms")
        create_journal = st.form_submit_button("新增期刊")
        if create_journal:
            terms = [term.strip() for term in keywords_terms.replace("\n", ",").split(",") if term.strip()]
            if new_journal_year_to and year_from > new_journal_year_to:
                st.warning("year_from must be less than or equal to year_to")
            else:
                payload = {
                    "name": journal_name,
                    "publisher": publisher or None,
                    "platform": platform or None,
                    "url": url or None,
                    "issn_print": issn_print or None,
                    "issn_electronic": issn_electronic or None,
                    "keywords": {"mode": keywords_mode, "terms": terms},
                    "year_from": int(year_from),
                    "year_to": int(new_journal_year_to) if new_journal_year_to else None,
                }
                status_code, result = api_post("/journals", json=payload)
                if status_code == 201:
                    st.success(f"journal #{result['id']}")
                    st.rerun()
                else:
                    st.warning(format_error_payload(result, status_code))
                    st.json(result)

    if journals_all:
        selected_journal = st.selectbox(
            "更新期刊",
            journals_all,
            format_func=journal_option_label,
        )
        active = st.checkbox("active", value=bool(selected_journal.get("active")), key=f"journal-active-{selected_journal['id']}")
        jy1, jy2 = st.columns(2)
        edit_year_from = jy1.number_input(
            "year_from",
            min_value=1900,
            max_value=2100,
            value=int(selected_journal.get("year_from") or 1990),
            key=f"journal-year-from-{selected_journal['id']}",
        )
        edit_year_to = jy2.number_input(
            "year_to",
            min_value=0,
            max_value=2100,
            value=int(selected_journal.get("year_to") or 0),
            key=f"journal-year-to-{selected_journal['id']}",
        )
        edit_keywords_mode = st.selectbox(
            "keywords_mode",
            ["or", "and"],
            index=1 if isinstance(selected_journal.get("keywords"), dict) and selected_journal["keywords"].get("mode") == "and" else 0,
            key=f"journal-keywords-mode-{selected_journal['id']}",
        )
        existing_terms = selected_journal.get("keywords", [])
        if isinstance(existing_terms, dict):
            existing_terms = existing_terms.get("terms", [])
        keywords_terms = st.text_area(
            "keywords_terms",
            value=", ".join(existing_terms),
            key=f"journal-keywords-terms-{selected_journal['id']}",
        )
        if st.button("更新期刊", key=f"update-journal-{selected_journal['id']}"):
            terms = [term.strip() for term in keywords_terms.replace("\n", ",").split(",") if term.strip()]
            if edit_year_to and edit_year_from > edit_year_to:
                st.warning("year_from must be less than or equal to year_to")
            else:
                status_code, result = api_put(
                    f"/journals/{selected_journal['id']}",
                    json={
                        "active": active,
                        "keywords": {"mode": edit_keywords_mode, "terms": terms},
                        "year_from": int(edit_year_from),
                        "year_to": int(edit_year_to) if edit_year_to else None,
                    },
                )
                if status_code < 400:
                    st.rerun()
                else:
                    st.warning(format_error_payload(result, status_code))
                    st.json(result)
        if st.button("停用期刊", key=f"delete-journal-{selected_journal['id']}"):
            status_code, result = api_delete(f"/journals/{selected_journal['id']}")
            if status_code < 400:
                st.rerun()
            else:
                st.warning(format_error_payload(result, status_code))
                st.json(result)

    st.divider()
    st.subheader("分类")
    st.dataframe(categories_all, use_container_width=True)
    with st.form("create-category-form"):
        st.markdown("新增分类")
        c1, c2 = st.columns(2)
        category_name = c1.text_input("name", key="new-category-name")
        category_slug = c2.text_input("slug", key="new-category-slug")
        description = st.text_area("description", key="new-category-description")
        parent_options = [None] + categories_all
        parent_choice = st.selectbox(
            "parent_id",
            parent_options,
            format_func=category_parent_option_label,
            key="new-category-parent",
        )
        create_category = st.form_submit_button("新增分类")
        if create_category:
            payload = {
                "name": category_name,
                "slug": category_slug,
                "description": description or None,
                "parent_id": parent_choice["id"] if parent_choice else None,
            }
            status_code, result = api_post("/categories", json=payload)
            if status_code == 201:
                st.success(f"category #{result['id']}")
                st.rerun()
            else:
                st.warning(format_error_payload(result, status_code))
                st.json(result)

with documents_tab:
    uploaded = st.file_uploader("PDF", type=["pdf"])
    paper_id = st.number_input("paper_id", min_value=0, value=0)
    if st.button("上传", disabled=uploaded is None):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/pdf")}
        data = {"paper_id": str(paper_id)} if paper_id else {}
        status, payload = api_post("/documents", files=files, data=data)
        if status == 201:
            st.success(f"document #{payload['id']}")
        elif status == 409 and payload.get("error", {}).get("code") == "document_duplicate":
            duplicate_document = payload.get("document") or {}
            st.info(
                f"已有文档 #{duplicate_document.get('id')} · "
                f"{duplicate_document.get('original_name') or duplicate_document.get('file_path') or 'duplicate PDF'}"
            )
            st.json(duplicate_document)
        else:
            st.warning(format_error_payload(payload, status))
            st.json(payload)
    documents_page_col, documents_page_size_col = st.columns(2)
    documents_page = documents_page_col.number_input("documents_page", min_value=1, value=1, key="documents-page")
    documents_page_size = documents_page_size_col.number_input(
        "documents_page_size",
        min_value=1,
        max_value=100,
        value=50,
        key="documents-page-size",
    )
    try:
        documents_response = api_get("/documents", page=int(documents_page), page_size=int(documents_page_size))
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    docs = documents_response["items"]
    st.caption(
        f"documents page {documents_response['page']} · "
        f"page_size {documents_response['page_size']} · "
        f"total {documents_response['total']}"
    )
    if not docs:
        st.info("暂无文档，请先上传 PDF。")
    else:
        selected = st.selectbox("文档", docs, format_func=document_option_label)
        try:
            document_detail = api_get(f"/documents/{selected['id']}")
        except FrontendApiError as exc:
            st.error(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
            st.stop()
        if document_detail.get("parse_error"):
            st.warning(f"parse_error: {document_detail['parse_error']}")
        for document_asset in document_asset_downloads(document_detail):
            if document_asset["exists"]:
                st.download_button(
                    document_asset["label"],
                    data=document_asset["data"],
                    file_name=document_asset["file_name"],
                    mime=document_asset["mime"],
                )
            else:
                st.warning(document_asset["missing_message"])
        st.caption(f"chemistry_status: {document_detail.get('chemistry_status') or 'unknown'}")
        if document_detail.get("chemistry_error"):
            st.warning(f"chemistry_error: {document_detail['chemistry_error']}")
        linked_paper = document_detail.get("paper")
        if linked_paper:
            st.caption(
                "关联论文: "
                f'{linked_paper.get("title") or "Untitled"} · '
                f'DOI: {linked_paper.get("doi") or "-"} · '
                f'{linked_paper.get("journal_name") or "-"} · '
                f'{linked_paper.get("published_date") or "-"}'
            )
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("解析"):
            status_code, parse_payload = api_post(f"/documents/{selected['id']}/parse")
            if status_code < 400:
                st.success("已创建解析任务")
            else:
                st.warning(format_error_payload(parse_payload, status_code))
            st.json(parse_payload)
        translation_target_lang = c2.text_input(
            "target_lang",
            value="zh",
            key=f"translation-target-lang-{selected['id']}",
        )
        if c2.button("翻译"):
            status_code, translate_payload = api_post(
                f"/documents/{selected['id']}/translate",
                json={"target_lang": translation_target_lang},
            )
            if status_code < 400:
                st.success("已创建翻译任务")
            else:
                st.warning(format_error_payload(translate_payload, status_code))
            st.json(translate_payload)
        if c3.button("索引"):
            status_code, index_payload = api_post(f"/documents/{selected['id']}/index")
            if status_code < 400:
                st.success("已创建索引任务")
            else:
                st.warning(format_error_payload(index_payload, status_code))
            st.json(index_payload)
        if c4.button("抽取"):
            status_code, extract_payload = api_post(f"/documents/{selected['id']}/extract-chemistry")
            if status_code < 400:
                st.success("已创建化学抽取任务")
            else:
                st.warning(format_error_payload(extract_payload, status_code))
            st.json(extract_payload)
        sections_page_col, sections_page_size_col = st.columns(2)
        sections_page = sections_page_col.number_input("sections_page", min_value=1, value=1, key=f"sections-page-{selected['id']}")
        sections_page_size = sections_page_size_col.number_input(
            "sections_page_size",
            min_value=1,
            max_value=100,
            value=20,
            key=f"sections-page-size-{selected['id']}",
        )
        chunks_page_col, chunks_page_size_col = st.columns(2)
        chunks_page = chunks_page_col.number_input("chunks_page", min_value=1, value=1, key=f"chunks-page-{selected['id']}")
        chunks_page_size = chunks_page_size_col.number_input(
            "chunks_page_size",
            min_value=1,
            max_value=100,
            value=20,
            key=f"chunks-page-size-{selected['id']}",
        )
        try:
            sections_response = api_get(
                f"/documents/{selected['id']}/sections",
                page=int(sections_page),
                page_size=int(sections_page_size),
            )
        except FrontendApiError as exc:
            st.error(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
            st.stop()
        sections = sections_response["items"]
        try:
            chunks = api_get(
                f"/documents/{selected['id']}/chunks",
                page=int(chunks_page),
                page_size=int(chunks_page_size),
            )
        except FrontendApiError as exc:
            st.error(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
            st.stop()
        index_status = chunks.get("index_status") or ("indexed" if chunks["indexed"] else "not_indexed")
        st.caption(f"index_status: {index_status} · chunks: {chunks['total']}")
        st.dataframe(document_status_rows(document_detail, chunks), use_container_width=True)
        if chunks.get("index_error"):
            st.warning(f"index_error: {chunks['index_error']}")
        section_tab, translation_tab, chunks_tab = st.tabs(["章节", "翻译预览", "索引"])
        with section_tab:
            if sections:
                section_preview = st.selectbox(
                    "section_preview",
                    sections,
                    format_func=document_section_option_label,
                )
                st.markdown(f"### {section_preview.get('title') or 'Section'}")
                st.write(section_preview.get("content") or "")
            st.caption(
                f"sections page {sections_response['page']} · "
                f"page_size {sections_response['page_size']} · "
                f"total {sections_response['total']}"
            )
            st.dataframe(document_section_rows(sections), use_container_width=True)
        with translation_tab:
            try:
                translation_preview = api_get(f"/documents/{selected['id']}/translation")
                st.caption(translation_preview.get("status"))
                translation_text = ""
                if translation_preview.get("status") == "failed":
                    translation_error = translation_preview.get("error") or "unknown error"
                    st.warning(f"translation failed: {translation_error}")
                    st.dataframe(translation_status_rows(translation_preview), use_container_width=True)
                    st.json(translation_preview)
                elif translation_preview.get("output_path"):
                    translation_file = translation_download(translation_preview)
                    if translation_file:
                        translation_text = translation_file["data"]
                        st.dataframe(
                            translation_status_rows(translation_preview, preview_text=translation_text),
                            use_container_width=True,
                        )
                        st.download_button(
                            translation_file["label"],
                            data=translation_file["data"],
                            file_name=translation_file["file_name"],
                            mime=translation_file["mime"],
                        )
                        st.markdown(translation_text[:4000])
                    else:
                        st.warning(f"翻译文件不存在: {translation_preview.get('output_path')}")
                        st.dataframe(translation_status_rows(translation_preview), use_container_width=True)
                        st.json(translation_preview)
                else:
                    st.dataframe(translation_status_rows(translation_preview), use_container_width=True)
                    st.json(translation_preview)
            except FrontendApiError as exc:
                translation_preview = None
                st.warning(format_error_payload(exc.payload, exc.status_code))
                st.json(exc.payload)
            except Exception as exc:
                translation_preview = None
                st.info(f"translation_preview unavailable: {exc}")
        with chunks_tab:
            if chunks["items"]:
                chunk_preview = st.selectbox(
                    "chunk / vector_id",
                    chunks["items"],
                    format_func=document_chunk_option_label,
                )
                st.code(chunk_preview.get("text") or "")
            st.caption(f"chunks page {chunks['page']} · page_size {chunks['page_size']} · total {chunks['total']}")
            st.dataframe(document_chunk_rows(chunks["items"]), use_container_width=True)

with rag_tab:
    rag_documents_page_col, rag_documents_page_size_col = st.columns(2)
    rag_documents_page = rag_documents_page_col.number_input("rag_documents_page", min_value=1, value=1, key="rag-documents-page")
    rag_documents_page_size = rag_documents_page_size_col.number_input(
        "rag_documents_page_size",
        min_value=1,
        max_value=100,
        value=100,
        key="rag-documents-page-size",
    )
    try:
        rag_documents_response = api_get("/documents", page=int(rag_documents_page), page_size=int(rag_documents_page_size))
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    rag_documents = rag_documents_response["items"]
    st.caption(
        f"RAG documents page {rag_documents_response['page']} · "
        f"page_size {rag_documents_response['page_size']} · "
        f"total {rag_documents_response['total']}"
    )
    if rag_documents:
        selected_rag_documents = st.multiselect(
            "限定文档",
            rag_documents,
            format_func=document_option_label,
            key="rag-document-select",
        )
    else:
        selected_rag_documents = []
        st.info("暂无可选文档，请先上传并索引文档。")
    doc_ids = st.text_input("document_ids", value="")
    question = st.text_input("问题", value="plasma chemistry")
    top_k = st.number_input("top_k", min_value=1, max_value=20, value=6)
    if st.button("提问"):
        try:
            selected_document_ids = [int(document["id"]) for document in selected_rag_documents]
            typed_document_ids = [int(part.strip()) for part in doc_ids.split(",") if part.strip()]
            ids = list(dict.fromkeys(selected_document_ids + typed_document_ids))
            document_id_error = None
        except ValueError:
            ids = []
            document_id_error = "document_ids 只能包含整数，用英文逗号分隔。"
        if document_id_error:
            st.warning(document_id_error)
        else:
            status, rag_payload = api_post(
                "/rag/query",
                json={"question": question, "document_ids": ids, "top_k": int(top_k)},
            )
            if status >= 400:
                st.warning(format_error_payload(rag_payload, status))
                st.json(rag_payload)
            else:
                answer = rag_payload.get("answer") or ""
                st.markdown(answer)
                sources = rag_source_rows(rag_payload.get("sources") or [])
                st.subheader("引用来源")
                if sources:
                    st.dataframe(sources, use_container_width=True)
                    source_preview = st.selectbox(
                        "source chunk",
                        sources,
                        format_func=rag_source_option_label,
                    )
                    if source_preview.get("source_excerpt"):
                        st.code(source_preview.get("source_excerpt"))
                    st.json(source_preview)
                else:
                    st.info("没有可定位引用来源。")
                with st.expander("raw RAG response"):
                    st.json(rag_payload)

with chemistry_tab:
    chemistry_documents_page_col, chemistry_documents_page_size_col = st.columns(2)
    chemistry_documents_page = chemistry_documents_page_col.number_input(
        "chemistry_documents_page",
        min_value=1,
        value=1,
        key="chemistry-documents-page",
    )
    chemistry_documents_page_size = chemistry_documents_page_size_col.number_input(
        "chemistry_documents_page_size",
        min_value=1,
        max_value=100,
        value=100,
        key="chemistry-documents-page-size",
    )
    try:
        chemistry_documents_response = api_get(
            "/documents",
            page=int(chemistry_documents_page),
            page_size=int(chemistry_documents_page_size),
        )
    except FrontendApiError as exc:
        st.error(format_error_payload(exc.payload, exc.status_code))
        st.json(exc.payload)
        st.stop()
    chemistry_documents = chemistry_documents_response["items"]
    st.caption(
        f"chemistry documents page {chemistry_documents_response['page']} · "
        f"page_size {chemistry_documents_response['page_size']} · "
        f"total {chemistry_documents_response['total']}"
    )
    if chemistry_documents:
        chemistry_document_options = chemistry_documents
        selected_chemistry_document = st.selectbox(
            "化学库文档",
            chemistry_document_options,
            format_func=document_option_label,
            key="chemistry-document-select",
        )
        chemistry_document_id = int(selected_chemistry_document["id"])
        st.caption(f"chemistry_document_id: {chemistry_document_id}")
    else:
        st.info("暂无可选文档，请先上传并抽取化学库。")
        chemistry_document_id = st.number_input("手动 document_id", min_value=1, value=1)
    reaction_sets_page_col, reaction_sets_page_size_col = st.columns(2)
    reaction_sets_page = reaction_sets_page_col.number_input(
        "reaction_sets_page",
        min_value=1,
        value=1,
        key="reaction-sets-page",
    )
    reaction_sets_page_size = reaction_sets_page_size_col.number_input(
        "reaction_sets_page_size",
        min_value=1,
        max_value=100,
        value=20,
        key="reaction-sets-page-size",
    )
    if st.button("加载文档反应集"):
        try:
            st.session_state["document_reaction_sets"] = api_get(
                f"/documents/{chemistry_document_id}/reaction-sets",
                page=int(reaction_sets_page),
                page_size=int(reaction_sets_page_size),
            )
        except FrontendApiError as exc:
            st.warning(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
            st.session_state["document_reaction_sets"] = None

    selected_reaction_set_id = None
    document_reaction_sets = st.session_state.get("document_reaction_sets")
    if document_reaction_sets:
        reaction_set_items = document_reaction_sets.get("items", [])
        st.caption(
            f"reaction sets page {document_reaction_sets['page']} · "
            f"page_size {document_reaction_sets['page_size']} · "
            f"total {document_reaction_sets['total']}"
        )
        st.dataframe(reaction_set_rows(reaction_set_items), use_container_width=True)
        if not reaction_set_items:
            st.info("该文档暂无反应集。")
        else:
            selected_reaction_set = st.selectbox(
                "document_reaction_sets",
                reaction_set_items,
                format_func=reaction_set_option_label,
            )
            selected_reaction_set_id = selected_reaction_set["id"]

    rs_id = st.number_input("reaction_set_id", min_value=1, value=int(selected_reaction_set_id or 1))
    load_reaction_set = st.button("加载反应集")
    should_load_reaction_set = load_reaction_set or selected_reaction_set_id is not None
    if should_load_reaction_set:
        try:
            st.session_state["reaction_set_detail"] = api_get(f"/reaction-sets/{rs_id}")
        except FrontendApiError as exc:
            st.warning(format_error_payload(exc.payload, exc.status_code))
            st.json(exc.payload)
            st.session_state["reaction_set_detail"] = None

    detail = st.session_state.get("reaction_set_detail")
    if detail:
        review_state = reaction_set_review_state(detail)
        reactions = review_state["reactions"]
        unverified_reactions = review_state["unverified_reactions"]
        reaction_count = review_state["reaction_count"]
        export_blocked = review_state["export_blocked"]
        st.caption(review_state["summary"])
        if review_state.get("source_note"):
            st.caption(f"source_note: {review_state['source_note']}")
        show_only_unverified = st.checkbox("只显示未复核", value=False, key="show_only_unverified")
        if unverified_reactions:
            st.subheader("未复核反应")
            st.dataframe(reaction_review_rows(reactions, only_unverified=True), use_container_width=True)
        if review_state["export_message"]:
            st.info(review_state["export_message"])
        export_format = st.selectbox("导出格式", ["json", "txt", "bolsig"], key="reaction_export_format")
        if st.button("导出反应集", key="export-reaction-set", disabled=export_blocked):
            status, payload = api_post(f"/reaction-sets/{rs_id}/export?format={export_format}", json=None)
            if status == 409:
                st.warning(format_error_payload(payload, status))
                st.json(payload)
            elif status >= 400:
                st.error(format_error_payload(payload, status))
                st.json(payload)
            else:
                st.success(payload["output_path"])
                st.dataframe(reaction_export_rows(payload), use_container_width=True)
                export_download = reaction_export_download(payload)
                if export_download:
                    st.download_button(
                        export_download["label"],
                        data=export_download["data"],
                        file_name=export_download["file_name"],
                        mime=export_download["mime"],
                    )
                else:
                    st.warning(f"导出文件不存在: {payload.get('output_path')}")
                st.json(payload)
        display_reactions = unverified_reactions if show_only_unverified else reactions
        for reaction in display_reactions:
            with st.container(border=True):
                display_state = reaction_display_state(reaction)
                st.write(display_state["reaction"])
                st.caption(display_state["source_summary"])
                if display_state["source_excerpt"]:
                    st.code(display_state["source_excerpt"])
                st.caption(display_state["species_summary"])
                c1, c2, c3 = st.columns(3)
                form_state = reaction_review_form_state(reaction)
                reaction_type = c1.selectbox(
                    "reaction_type",
                    form_state["reaction_type_options"],
                    index=form_state["reaction_type_index"],
                    key=f"reaction-type-{reaction['id']}",
                )
                rate_type = c2.selectbox(
                    "rate_type",
                    form_state["rate_type_options"],
                    index=form_state["rate_type_index"],
                    key=f"rate-type-{reaction['id']}",
                )
                include_threshold_ev = c3.checkbox(
                    "include_threshold_ev",
                    value=form_state["include_threshold_ev"],
                    key=f"include-threshold-ev-{reaction['id']}",
                )
                threshold_ev = c3.number_input(
                    "threshold_ev",
                    value=form_state["threshold_ev_value"],
                    disabled=not include_threshold_ev,
                    key=f"threshold-ev-{reaction['id']}",
                )
                rate_value = st.text_area(
                    "rate_value",
                    value=form_state["rate_value"],
                    key=f"rate-value-{reaction['id']}",
                )
                cross_section_url = st.text_input(
                    "cross_section_url",
                    value=form_state["cross_section_url"],
                    key=f"cross-section-url-{reaction['id']}",
                )
                verified_by = st.text_input(
                    "verified_by",
                    value=form_state["verified_by"],
                    key=f"verified-by-{reaction['id']}",
                )
                verified = st.checkbox(
                    "verified",
                    value=form_state["verified"],
                    key=f"verified-{reaction['id']}",
                )
                if reaction.get("audit_log"):
                    with st.expander("audit_log"):
                        st.dataframe(reaction_audit_rows(reaction["audit_log"]), use_container_width=True)
                        st.json(reaction["audit_log"])
                if st.button("保存复核", key=f"verify-{reaction['id']}"):
                    payload = reaction_review_payload(
                        verified=verified,
                        reaction_type=reaction_type,
                        rate_type=rate_type,
                        rate_value=rate_value,
                        include_threshold_ev=include_threshold_ev,
                        threshold_ev=threshold_ev,
                        cross_section_url=cross_section_url,
                        verified_by=verified_by,
                    )
                    status_code, result = api_put(f"/reactions/{reaction['id']}/verify", json=payload)
                    if status_code < 400:
                        st.session_state["reaction_set_detail"] = result
                        st.session_state["reaction_review_message"] = "已保存复核结果"
                        st.rerun()
                    else:
                        st.warning(format_error_payload(result, status_code))
                        st.json(result)
