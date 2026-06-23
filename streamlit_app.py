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
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="paper-lab-agent", layout="wide")
st.title("paper-lab-agent")

try:
    health = api_get("/health")
    st.caption(f"{health['service']} · {health['status']}")
except Exception as exc:
    st.error(f"API unavailable: {exc}")
    st.stop()

search_tab, documents_tab, rag_tab, chemistry_tab = st.tabs(["检索", "文档", "问答", "化学库"])

with st.sidebar:
    st.subheader("系统")
    status = api_get("/system/status")
    st.metric("期刊", status["counts"]["journals"])
    st.metric("论文", status["counts"]["papers"])
    st.metric("文档", status["counts"]["documents"])
    st.caption(f"DB: {status['database_path']}")

with search_tab:
    st.caption("可先运行 `python scripts/import_fixtures.py` 导入离线样例。")
    journals = api_get("/journals", active=True, page_size=100)["items"]
    categories = api_get("/categories")["items"]
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    q = col1.text_input("关键词", value="plasma")
    journal_names = ["全部"] + [j["name"] for j in journals]
    journal_choice = col2.selectbox("期刊", journal_names)
    category_slugs = ["全部"] + [c["slug"] for c in categories]
    category_choice = col3.selectbox("分类", category_slugs)
    oa_only = col4.checkbox("OA only")
    params = {
        "q": q or None,
        "page_size": 20,
        "oa_only": oa_only,
    }
    if journal_choice != "全部":
        params["journal_id"] = next(j["id"] for j in journals if j["name"] == journal_choice)
    if category_choice != "全部":
        params["category"] = category_choice
    papers = api_get("/papers", **{k: v for k, v in params.items() if v is not None})
    st.metric("结果", papers["total"])
    for paper in papers["items"]:
        with st.container(border=True):
            st.subheader(paper["title"])
            st.caption(f"{paper.get('journal_name') or '-'} · {paper.get('published_date') or '-'} · {paper.get('oa_status') or 'unknown'}")
            st.write((paper.get("abstract") or "")[:400])
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
    st.dataframe(api_get("/crawl/jobs", page_size=10)["items"], use_container_width=True)

with documents_tab:
    uploaded = st.file_uploader("PDF", type=["pdf", "txt"])
    paper_id = st.number_input("paper_id", min_value=0, value=0)
    if st.button("上传", disabled=uploaded is None):
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type or "application/pdf")}
        data = {"paper_id": str(paper_id)} if paper_id else {}
        status, payload = api_post("/documents", files=files, data=data)
        if status == 201:
            st.success(f"document #{payload['id']}")
        else:
            st.warning(payload)
    docs = api_get("/documents", page_size=50)["items"]
    if docs:
        selected = st.selectbox("文档", docs, format_func=lambda d: f"#{d['id']} {d.get('original_name') or Path(d['file_path']).name} · {d['parse_status']}")
        c1, c2, c3, c4 = st.columns(4)
        if c1.button("解析"):
            st.json(api_post(f"/documents/{selected['id']}/parse")[1])
        if c2.button("翻译"):
            st.json(api_post(f"/documents/{selected['id']}/translate", json={"target_lang": "zh"})[1])
        if c3.button("索引"):
            st.json(api_post(f"/documents/{selected['id']}/index")[1])
        if c4.button("抽取"):
            st.json(api_post(f"/documents/{selected['id']}/extract-chemistry")[1])
        st.dataframe(api_get(f"/documents/{selected['id']}/sections")["items"], use_container_width=True)

with rag_tab:
    doc_ids = st.text_input("document_ids", value="")
    question = st.text_input("问题", value="plasma chemistry")
    if st.button("提问"):
        ids = [int(part.strip()) for part in doc_ids.split(",") if part.strip()]
        st.json(api_post("/rag/query", json={"question": question, "document_ids": ids, "top_k": 6})[1])

with chemistry_tab:
    rs_id = st.number_input("reaction_set_id", min_value=1, value=1)
    if st.button("加载反应集"):
        status, payload = api_post(f"/reaction-sets/{rs_id}/export", json=None)
        if status == 409:
            st.warning(payload)
        detail = api_get(f"/reaction-sets/{rs_id}")
        st.json(detail)
        for reaction in detail.get("reactions", []):
            with st.container(border=True):
                st.write(reaction["reaction"])
                rate_value = st.text_input("rate_value", value=reaction.get("rate_value") or "", key=f"rate-{reaction['id']}")
                if st.button("复核通过", key=f"verify-{reaction['id']}"):
                    st.json(api_put(f"/reactions/{reaction['id']}/verify", json={"verified": True, "rate_value": rate_value, "verified_by": "streamlit"}))
