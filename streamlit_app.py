import os
from pathlib import Path

import requests
import streamlit as st


API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api/v1").rstrip("/")


def api_get(path: str, **params):
    response = requests.get(f"{API_BASE}{path}", params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def api_post(path: str, json=None, files=None, data=None):
    response = requests.post(f"{API_BASE}{path}", json=json, files=files, data=data, timeout=60)
    if response.status_code >= 400:
        return response.status_code, response.json()
    return response.status_code, response.json()


def api_put(path: str, json=None):
    response = requests.put(f"{API_BASE}{path}", json=json, timeout=20)
    return response.status_code, response.json()


def flatten_crawl_job_rows(jobs: list[dict]) -> list[dict]:
    rows = []
    for job in jobs:
        diagnostics = job.get("diagnostics") or {}
        journal = job.get("journal") or {}
        rows.append(
            {
                "id": job.get("id") or job.get("job_id"),
                "journal": journal.get("name") or diagnostics.get("journal_name") or job.get("journal_id"),
                "status": diagnostics.get("status") or job.get("status"),
                "period": diagnostics.get("period") or job.get("period"),
                "date_from": diagnostics.get("date_from") or job.get("date_from"),
                "date_to": diagnostics.get("date_to") or job.get("date_to"),
                "found": diagnostics.get("papers_found", 0),
                "filtered": diagnostics.get("papers_filtered", 0),
                "accepted": diagnostics.get("papers_accepted", 0),
                "existing": diagnostics.get("papers_existing", 0),
                "new": diagnostics.get("papers_new", 0),
                "error": diagnostics.get("error") or job.get("error"),
            }
        )
    return rows


st.set_page_config(page_title="paper-lab-agent", layout="wide")
st.title("paper-lab-agent")

try:
    health = api_get("/health")
    st.caption(f"{health['service']} · {health['status']}")
except Exception as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

search_tab, config_tab, documents_tab, rag_tab, chemistry_tab = st.tabs(["检索", "配置", "文档", "问答", "化学库"])

with st.sidebar:
    st.subheader("系统")
    status = api_get("/system/status")
    st.metric("期刊", status["counts"]["journals"])
    st.metric("论文", status["counts"]["papers"])
    st.metric("文档", status["counts"]["documents"])
    runtime = status.get("runtime", {})
    st.caption(f"API: {runtime.get('api_prefix', '/api/v1')}")
    st.caption(f"scheduler_enabled: {runtime.get('scheduler_enabled', False)}")
    st.caption(f"DB: {status['database_path']}")

with search_tab:
    st.caption("可先运行 `python scripts/import_fixtures.py` 导入离线样例。")
    journals = api_get("/journals", active=True, page_size=100)["items"]
    categories = api_get("/categories")["items"]
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])
    q = col1.text_input("关键词", value="plasma")
    journal_names = ["全部"] + [j["name"] for j in journals]
    journal_choice = col2.selectbox("期刊", journal_names)
    category_slugs = ["全部"] + [c["slug"] for c in categories]
    category_choice = col3.selectbox("分类", category_slugs)
    year_from = col4.number_input("year_from", min_value=0, max_value=2100, value=0)
    year_to = col5.number_input("year_to", min_value=0, max_value=2100, value=0)
    oa_only = col6.checkbox("OA only")
    params = {
        "q": q or None,
        "page_size": 20,
        "oa_only": oa_only,
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
    else:
        papers = api_get("/papers", **{k: v for k, v in params.items() if v is not None})
    st.metric("结果", papers["total"])
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
            categories_text = ", ".join(paper.get("categories") or []) or "-"
            st.caption(f"分类结果: {categories_text}")
            if st.button("触发分类", key=f"classify-paper-{paper['id']}"):
                status_code, classified_paper = api_post(f"/papers/{paper['id']}/classify")
                if status_code < 400:
                    st.success(", ".join(classified_paper.get("categories") or []) or "无分类")
                else:
                    st.warning(classified_paper)
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
    crawl_journal_id = crawl_col1.number_input("journal_id", min_value=0, value=0)
    date_from = crawl_col2.text_input("date_from", value="")
    date_to = crawl_col3.text_input("date_to", value="")
    if st.button("创建抓取任务"):
        body = {"period": "manual"}
        if crawl_journal_id:
            body["journal_ids"] = [int(crawl_journal_id)]
        if date_from:
            body["date_from"] = date_from
        if date_to:
            body["date_to"] = date_to
        st.json(api_post("/crawl/run", json=body)[1])
    jobs = api_get("/crawl/jobs", page_size=10)["items"]
    st.dataframe(flatten_crawl_job_rows(jobs), use_container_width=True)
    if jobs:
        selected_job = st.selectbox(
            "任务详情",
            jobs,
            format_func=lambda job: f"#{job['id']} · journal {job.get('journal_id') or '-'} · {job.get('status')}",
        )
        job_detail = api_get(f"/crawl/jobs/{selected_job['id']}")
        diagnostics = job_detail.get("diagnostics", {})
        j1, j2, j3, j4 = st.columns(4)
        j1.metric("found", diagnostics.get("papers_found", 0))
        j2.metric("filtered", diagnostics.get("papers_filtered", 0))
        j3.metric("accepted", diagnostics.get("papers_accepted", 0))
        j4.metric("new", diagnostics.get("papers_new", 0))
        if diagnostics.get("error"):
            st.warning(diagnostics["error"])
        st.dataframe([diagnostics], use_container_width=True)
        st.json(job_detail)

with config_tab:
    journals_response = api_get("/journals", page_size=100)
    categories_response = api_get("/categories")
    journals_all = journals_response["items"]
    categories_all = categories_response["items"]

    st.subheader("期刊白名单")
    st.dataframe(journals_all, use_container_width=True)

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
        platform = j6.text_input("platform", key="new-journal-platform")
        url = st.text_input("url", key="new-journal-url")
        keywords_mode = st.selectbox("keywords_mode", ["or", "and"], key="new-journal-keywords-mode")
        keywords_terms = st.text_area("keywords_terms", key="new-journal-keywords-terms")
        create_journal = st.form_submit_button("新增期刊")
        if create_journal:
            terms = [term.strip() for term in keywords_terms.replace("\n", ",").split(",") if term.strip()]
            payload = {
                "name": journal_name,
                "publisher": publisher or None,
                "platform": platform or None,
                "url": url or None,
                "issn_print": issn_print or None,
                "issn_electronic": issn_electronic or None,
                "keywords": {"mode": keywords_mode, "terms": terms},
                "year_from": int(year_from),
            }
            status_code, result = api_post("/journals", json=payload)
            if status_code == 201:
                st.success(f"journal #{result['id']}")
                st.rerun()
            else:
                st.warning(result)

    if journals_all:
        selected_journal = st.selectbox(
            "更新期刊",
            journals_all,
            format_func=lambda journal: f"#{journal['id']} {journal['name']} · active={journal.get('active')}",
        )
        active = st.checkbox("active", value=bool(selected_journal.get("active")), key=f"journal-active-{selected_journal['id']}")
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
            status_code, result = api_put(
                f"/journals/{selected_journal['id']}",
                json={"active": active, "keywords": {"mode": edit_keywords_mode, "terms": terms}},
            )
            if status_code < 400:
                st.rerun()
            else:
                st.warning(result)

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
            format_func=lambda category: "无" if category is None else f"#{category['id']} {category['slug']}",
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
                st.warning(result)

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
            st.warning(payload)
    docs = api_get("/documents", page_size=50)["items"]
    if docs:
        selected = st.selectbox("文档", docs, format_func=lambda d: f"#{d['id']} {d.get('original_name') or Path(d['file_path']).name} · {d['parse_status']}")
        document_detail = api_get(f"/documents/{selected['id']}")
        if document_detail.get("parse_error"):
            st.warning(f"parse_error: {document_detail['parse_error']}")
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
            st.json(api_post(f"/documents/{selected['id']}/parse")[1])
        if c2.button("翻译"):
            st.json(api_post(f"/documents/{selected['id']}/translate", json={"target_lang": "zh"})[1])
        if c3.button("索引"):
            st.json(api_post(f"/documents/{selected['id']}/index")[1])
        if c4.button("抽取"):
            st.json(api_post(f"/documents/{selected['id']}/extract-chemistry")[1])
        sections = api_get(f"/documents/{selected['id']}/sections")["items"]
        chunks = api_get(f"/documents/{selected['id']}/chunks")
        index_status = "indexed" if chunks["indexed"] else "not indexed"
        st.caption(f"index_status: {index_status} · chunks: {chunks['total']}")
        section_tab, translation_tab, chunks_tab = st.tabs(["章节", "翻译预览", "索引"])
        with section_tab:
            if sections:
                section_preview = st.selectbox(
                    "section_preview",
                    sections,
                    format_func=lambda section: f"{section.get('seq')}. {section.get('title') or section.get('section_type')}",
                )
                st.markdown(f"### {section_preview.get('title') or 'Section'}")
                st.write(section_preview.get("content") or "")
            st.dataframe(sections, use_container_width=True)
        with translation_tab:
            try:
                translation_preview = api_get(f"/documents/{selected['id']}/translation")
                st.caption(translation_preview.get("status"))
                if translation_preview.get("status") == "failed":
                    translation_error = translation_preview.get("error") or "unknown error"
                    st.warning(f"translation failed: {translation_error}")
                    st.json(translation_preview)
                elif translation_preview.get("output_path") and Path(translation_preview.get("output_path")).exists():
                    output_path = Path(translation_preview.get("output_path"))
                    translation_text = output_path.read_text(encoding="utf-8")
                    st.download_button(
                        "下载双语翻译",
                        data=translation_text,
                        file_name=output_path.name,
                        mime="text/markdown",
                    )
                    st.markdown(translation_text[:4000])
                else:
                    st.json(translation_preview)
            except Exception as exc:
                translation_preview = None
                st.info(f"translation_preview unavailable: {exc}")
        with chunks_tab:
            if chunks["items"]:
                chunk_preview = st.selectbox(
                    "chunk / vector_id",
                    chunks["items"],
                    format_func=lambda chunk: f"{chunk.get('vector_id') or chunk.get('id')} · {chunk.get('section_title') or '-'}",
                )
                st.code(chunk_preview.get("text") or "")
            st.dataframe(chunks["items"], use_container_width=True)

with rag_tab:
    doc_ids = st.text_input("document_ids", value="")
    question = st.text_input("问题", value="plasma chemistry")
    if st.button("提问"):
        ids = [int(part.strip()) for part in doc_ids.split(",") if part.strip()]
        status, rag_payload = api_post("/rag/query", json={"question": question, "document_ids": ids, "top_k": 6})
        if status >= 400:
            st.warning(rag_payload)
        else:
            answer = rag_payload.get("answer") or ""
            st.markdown(answer)
            sources = rag_payload.get("sources") or []
            st.subheader("引用来源")
            if sources:
                st.dataframe(sources, use_container_width=True)
                source_preview = st.selectbox(
                    "source chunk",
                    sources,
                    format_func=lambda source: (
                        f"doc {source.get('document_id')} · "
                        f"chunk_id={source.get('chunk_id')} · "
                        f"{source.get('section_title') or '-'}"
                    ),
                )
                st.json(source_preview)
            else:
                st.info("没有可定位引用来源。")
            with st.expander("raw RAG response"):
                st.json(rag_payload)

with chemistry_tab:
    chemistry_document_id = st.number_input("chemistry_document_id", min_value=1, value=1)
    if st.button("加载文档反应集"):
        try:
            st.session_state["document_reaction_sets"] = api_get(f"/documents/{chemistry_document_id}/reaction-sets")
        except Exception as exc:
            st.warning(exc)
            st.session_state["document_reaction_sets"] = None

    selected_reaction_set_id = None
    document_reaction_sets = st.session_state.get("document_reaction_sets")
    if document_reaction_sets:
        reaction_set_items = document_reaction_sets.get("items", [])
        st.dataframe(reaction_set_items)
        if reaction_set_items:
            selected_reaction_set = st.selectbox(
                "document_reaction_sets",
                reaction_set_items,
                format_func=lambda item: f"#{item['id']} · {item.get('status') or 'unknown'} · {item.get('name') or 'Reaction set'}",
            )
            selected_reaction_set_id = selected_reaction_set["id"]

    rs_id = st.number_input("reaction_set_id", min_value=1, value=int(selected_reaction_set_id or 1))
    if st.button("加载反应集") or "reaction_set_detail" not in st.session_state:
        try:
            st.session_state["reaction_set_detail"] = api_get(f"/reaction-sets/{rs_id}")
        except Exception as exc:
            st.warning(exc)
            st.session_state["reaction_set_detail"] = None

    detail = st.session_state.get("reaction_set_detail")
    if detail:
        reactions = detail.get("reactions", [])
        unverified_reactions = [reaction for reaction in reactions if not reaction.get("verified")]
        st.caption(f"status: {detail.get('status')} · reactions: {len(reactions)} · 未复核: {len(unverified_reactions)}")
        show_only_unverified = st.checkbox("只显示未复核", value=False, key="show_only_unverified")
        export_blocked = bool(unverified_reactions)
        if export_blocked:
            st.info("未全复核不可导出：请先完成所有反应复核。")
        export_format = st.selectbox("导出格式", ["json", "txt", "bolsig"], key="reaction_export_format")
        if st.button("导出反应集", key="export-reaction-set", disabled=export_blocked):
            status, payload = api_post(f"/reaction-sets/{rs_id}/export?format={export_format}", json=None)
            if status == 409:
                st.warning(payload)
            elif status >= 400:
                st.error(payload)
            else:
                st.success(payload["output_path"])
                export_path = Path(payload["output_path"])
                if export_path.exists():
                    export_text = export_path.read_text(encoding="utf-8")
                    st.download_button(
                        "下载导出文件",
                        data=export_text,
                        file_name=export_path.name,
                        mime=payload.get("mime_type") or "text/plain",
                    )
                st.json(payload)
        display_reactions = unverified_reactions if show_only_unverified else reactions
        for reaction in display_reactions:
            with st.container(border=True):
                st.write(reaction["reaction"])
                st.caption(
                    f"verified: {bool(reaction.get('verified'))} · "
                    f"confidence: {reaction.get('confidence')} · "
                    f"source_section_id: {reaction.get('source_section_id')}"
                )
                source_excerpt = reaction.get("source_excerpt")
                if source_excerpt:
                    st.code(source_excerpt)
                c1, c2, c3 = st.columns(3)
                reaction_type = c1.text_input(
                    "reaction_type",
                    value=reaction.get("reaction_type") or "",
                    key=f"reaction-type-{reaction['id']}",
                )
                rate_type = c2.text_input(
                    "rate_type",
                    value=reaction.get("rate_type") or "",
                    key=f"rate-type-{reaction['id']}",
                )
                threshold_ev = c3.number_input(
                    "threshold_ev",
                    value=float(reaction["threshold_ev"]) if reaction.get("threshold_ev") is not None else 0.0,
                    key=f"threshold-ev-{reaction['id']}",
                )
                rate_value = st.text_area(
                    "rate_value",
                    value=reaction.get("rate_value") or "",
                    key=f"rate-value-{reaction['id']}",
                )
                cross_section_url = st.text_input(
                    "cross_section_url",
                    value=reaction.get("cross_section_url") or "",
                    key=f"cross-section-url-{reaction['id']}",
                )
                verified_by = st.text_input("verified_by", value="streamlit", key=f"verified-by-{reaction['id']}")
                verified = st.checkbox("verified", value=bool(reaction.get("verified")), key=f"verified-{reaction['id']}")
                if reaction.get("audit_log"):
                    with st.expander("audit_log"):
                        st.json(reaction["audit_log"])
                if st.button("保存复核", key=f"verify-{reaction['id']}"):
                    payload = {
                        "verified": verified,
                        "reaction_type": reaction_type or None,
                        "rate_type": rate_type or None,
                        "rate_value": rate_value or None,
                        "threshold_ev": threshold_ev if threshold_ev else None,
                        "cross_section_url": cross_section_url or None,
                        "verified_by": verified_by or None,
                    }
                    status_code, result = api_put(f"/reactions/{reaction['id']}/verify", json=payload)
                    if status_code < 400:
                        st.session_state["reaction_set_detail"] = result
                        st.rerun()
                    else:
                        st.warning(result)
