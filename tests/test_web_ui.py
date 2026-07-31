import os
import re
from pathlib import Path

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def make_client(tmp_path):
    os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
    os.environ["PAPER_LAB_DATA_DIR"] = str(tmp_path)
    os.environ["PAPER_LAB_PDF_DIR"] = str(tmp_path / "pdfs")
    os.environ["PAPER_LAB_TEI_DIR"] = str(tmp_path / "tei")
    os.environ["PAPER_LAB_TRANSLATION_DIR"] = str(tmp_path / "translations")
    os.environ["PAPER_LAB_EXPORT_DIR"] = str(tmp_path / "exports")
    os.environ["VECTOR_DB_PATH"] = str(tmp_path / "vector-index.json")

    from app.config import get_settings
    from app.db import init_db
    from app.main import app
    from fastapi.testclient import TestClient

    get_settings.cache_clear()
    init_db()
    return TestClient(app)


def seed_translated_document(tmp_path, conn_module, markdown: str) -> int:
    with conn_module.get_conn() as conn:
        document_id = conn.execute(
            "INSERT INTO documents (file_path, parse_status) VALUES ('doc.pdf', 'parsed')"
        ).lastrowid
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 1, 'Abstract', 'Argon plasma abstract.', 'abstract')
            """,
            (document_id,),
        )
        conn.execute(
            """
            INSERT INTO sections (document_id, seq, title, content, section_type)
            VALUES (?, 2, 'Table 1', 'rate table', 'table')
            """,
            (document_id,),
        )
        output_path = tmp_path / "translations" / f"document-{document_id}-zh.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, output_path)
            VALUES (?, 'en', 'zh', 'done', ?)
            """,
            (document_id, str(output_path)),
        )
    return document_id


BILINGUAL_MARKDOWN = """# Bilingual Translation

> Translated with configured model `gpt-4o-mini`.

## Abstract

### Source

Argon plasma abstract.

### zh

氩等离子体摘要。

## Table 1

### Source

rate table

### zh

> Section type `table` is preserved without machine translation.

rate table
"""


def test_parse_translation_markdown_splits_source_and_target_blocks():
    from app.services.translation import parse_translation_markdown

    blocks = parse_translation_markdown(BILINGUAL_MARKDOWN)

    assert [block["title"] for block in blocks] == ["Abstract", "Table 1"]
    assert blocks[0]["source"] == "Argon plasma abstract."
    assert blocks[0]["target"] == "氩等离子体摘要。"
    assert blocks[0]["note"] is None


def test_parse_translation_markdown_keeps_preserved_section_note_out_of_target():
    from app.services.translation import parse_translation_markdown

    blocks = parse_translation_markdown(BILINGUAL_MARKDOWN)

    assert blocks[1]["note"] == "Section type `table` is preserved without machine translation."
    assert blocks[1]["target"] == "rate table"


def test_parse_translation_markdown_returns_empty_list_for_blank_output():
    from app.services.translation import parse_translation_markdown

    assert parse_translation_markdown("") == []


def test_read_translation_markdown_ignores_missing_output_path(tmp_path):
    from app.services.translation import read_translation_markdown

    assert read_translation_markdown(None) == ""
    assert read_translation_markdown(str(tmp_path / "absent.md")) == ""


def test_read_translation_markdown_ignores_symlinked_output(tmp_path):
    from app.services.translation import read_translation_markdown

    real = tmp_path / "real.md"
    real.write_text("## Abstract\n", encoding="utf-8")
    link = tmp_path / "link.md"
    link.symlink_to(real)

    assert read_translation_markdown(str(link)) == ""


def test_translation_sections_align_blocks_with_document_sections(tmp_path):
    client = make_client(tmp_path)
    from app import db
    from app.services.translation import translation_sections

    document_id = seed_translated_document(tmp_path, db, BILINGUAL_MARKDOWN)
    output_path = str(tmp_path / "translations" / f"document-{document_id}-zh.md")

    sections = translation_sections(document_id, output_path)

    assert [section["seq"] for section in sections] == [1, 2]
    assert [section["section_type"] for section in sections] == ["abstract", "table"]
    assert sections[0]["target"] == "氩等离子体摘要。"
    assert sections[0]["section_id"] is not None
    assert client is not None


def test_get_translation_endpoint_returns_reader_sections(tmp_path):
    client = make_client(tmp_path)
    from app import db

    document_id = seed_translated_document(tmp_path, db, BILINGUAL_MARKDOWN)

    response = client.get(f"/api/v1/documents/{document_id}/translation")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "done"
    assert [section["title"] for section in payload["sections"]] == ["Abstract", "Table 1"]
    assert payload["sections"][0]["source"] == "Argon plasma abstract."
    assert payload["sections"][0]["target"] == "氩等离子体摘要。"


def test_get_translation_endpoint_returns_empty_sections_when_output_missing(tmp_path):
    client = make_client(tmp_path)
    from app import db

    with db.get_conn() as conn:
        document_id = conn.execute(
            "INSERT INTO documents (file_path, parse_status) VALUES ('doc.pdf', 'parsed')"
        ).lastrowid
        conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status, error)
            VALUES (?, 'en', 'zh', 'failed', 'document has no parsed sections')
            """,
            (document_id,),
        )

    payload = client.get(f"/api/v1/documents/{document_id}/translation").json()

    assert payload["status"] == "failed"
    assert payload["sections"] == []


def test_root_redirects_to_web_ui(tmp_path):
    client = make_client(tmp_path)

    response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/ui/"


def test_web_ui_index_and_assets_are_served(tmp_path):
    client = make_client(tmp_path)

    index = client.get("/ui/")
    assert index.status_code == 200
    assert "等离子体文献工作台" in index.text
    assert "PLASMA LITERATURE WORKBENCH" in index.text

    for asset in ("/ui/app.js", "/ui/styles.css"):
        assert client.get(asset).status_code == 200


def test_web_ui_health_and_docs_routes_still_resolve(tmp_path):
    client = make_client(tmp_path)

    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/api/v1/health").json()["status"] == "ok"
    assert client.get("/openapi.json").status_code == 200


def test_web_ui_assets_are_self_contained():
    """The locked stack forbids pulling in a frontend framework or CDN at runtime."""
    sources = "\n".join(
        (WEB_DIR / name).read_text(encoding="utf-8") for name in ("index.html", "app.js", "styles.css")
    )
    remote = re.findall(r"""(?:src|href)=["'](https?://[^"']+)""", sources)

    assert remote == []


def test_web_ui_calls_only_documented_api_prefix():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "const API = '/api/v1';" in app_js
    assert "fetch(API + path" in app_js


def test_web_ui_does_not_show_translated_author_names():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "function untranslatedAuthorName(value)" in app_js
    assert "if (!hasLatin || !hasHan) return name;" in app_js
    assert ".map((a) => untranslatedAuthorName(" in app_js


def test_web_ui_separates_local_search_from_online_sync():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="search-source"' not in index
    assert "默认检索本地库 · 在线同步" not in app_js
    assert 'id="do-search">检索本地库</button>' in index
    assert 'id="do-online-search">联网搜索</button>' in index
    assert index.index('id="do-online-search"') < index.index('id="do-search"')
    assert 'id="search-mode"' in index
    assert 'id="search-limit"' in index
    assert "async function runOnlineSearch()" in app_js
    assert "api('/crawl/run', { method: 'POST', body })" in app_js
    assert "search_terms: searchTerms" in app_js
    assert "search_mode: state.queryMode" in app_js
    assert "max_results: state.resultLimit" in app_js
    assert "if (accepted.cache_hit)" in app_js
    assert "await waitForCrawlJobs(jobIds)" in app_js
    assert "await runSearch(true, { keepSyncSummary: true })" in app_js
    assert "Date.now() + 1800000" in app_js
    assert "联网搜索等待超过 30 分钟" in app_js


def test_web_ui_library_omits_redundant_file_hash_summary():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="lib-sub"' not in index
    assert "共 ${state.documents.length} 篇 · 上传 PDF 后按 file_hash 去重" not in app_js


def test_web_ui_library_upload_starts_automatic_document_processing():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "自动解析、翻译、建立 RAG 索引并抽取化学库" in index
    assert "form.append('auto_process', 'true')" in app_js
    assert "form.append('target_lang', persisted.targetLang)" in app_js
    assert "${file.name} 已上传，正在自动处理…" in app_js
    assert "api(`/documents/${doc.id}/parse`, { method: 'POST' }).catch(() => {});" not in app_js


def test_web_ui_groups_fulltext_filters_and_keeps_oa_download_modes_exclusive():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert '<span class="chips-label">全文</span>' in index
    assert 'id="oa-chip" title="只看有开放全文链接的论文">OA</button>' in index
    assert 'id="download-chip" title="只看系统支持直接下载的论文">下载</button>' in index
    assert "downloadOnly: false" in app_js
    assert "params.set('downloadable_only', 'true')" in app_js
    assert "if (state.oaOnly) state.downloadOnly = false;" in app_js
    assert "if (state.downloadOnly) state.oaOnly = false;" in app_js


def test_web_ui_download_queue_only_launches_supported_oa_fulltext():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="download-summary"' in index
    assert 'id="download-marked" disabled>一键下载可用全文</button>' in index
    assert "function downloadAvailability(paper)" in app_js
    assert "hostname === 'example.test'" in app_js
    assert "未发现开放全文" in app_js
    assert "开放权限未知" in app_js
    assert "测试数据不支持下载" in app_js
    assert "async function downloadMarkedPapers()" in app_js
    assert "entries.filter((paper) => downloadAvailability(paper).supported)" in app_js
    assert "fetch(`${API}/papers/${encodeURIComponent(paper.id)}/download`)" in app_js
    assert "const blob = await response.blob()" in app_js
    assert "state.markedDownloadState[paper.id] = 'downloading'" in app_js
    assert "state.markedDownloadState[paper.id] = 'downloaded'" in app_js
    assert "state.markedDownloadState[paper.id] = 'failed'" in app_js
    assert "已下载 ${downloaded} 篇" in app_js
    assert "link.target = '_blank'" not in app_js
    assert ".mk-status.downloading" in styles
    assert ".mk-status.downloaded" in styles
    assert ".mk-status.failed" in styles
    assert ".mk-status.off" in styles
    assert ".drawer-download-all" in styles


def test_web_ui_download_queue_persists_and_refreshes_oa_metadata():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "oa_status: paper.oa_status || 'unknown'" in app_js
    assert "oa_pdf_url: downloadInfo.url" in app_js
    assert "async function refreshMarkedDownloadInfo()" in app_js
    assert "apiOrNull(`/papers/${marked.id}`)" in app_js
    assert "refreshMarkedDownloadInfo();" in app_js
    assert "暂不支持下载" in app_js


def test_web_ui_reader_can_retranslate_current_document():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="reader-retranslate" disabled>再次翻译</button>' in index
    assert "async function retranslateReader()" in app_js
    assert "async function waitForTranslationJob(" in app_js
    assert "translation.id === translationId && translation.status === 'done'" in app_js
    assert "api(`/documents/${docId}/translate`" in app_js
    assert "body: { target_lang: targetLang }" in app_js
    assert "await openReader(docId)" in app_js
    assert "$('#reader-retranslate').addEventListener('click', retranslateReader)" in app_js


def test_web_ui_reader_can_open_current_paper_ai_qa_split():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert "{ k: 'qa', l: 'AI 问答' }" in app_js
    assert 'id="reader-qa-language"' in index
    assert 'data-reader-lang="zh"' in index
    assert 'data-reader-lang="en"' in index
    assert 'id="reader-chat-panel"' in index
    assert 'id="reader-chat-log"' in index
    assert 'id="reader-chat-input"' in index
    assert "state.readerQaLang = btn.dataset.readerLang" in app_js
    assert "body: { question, document_ids: [docId], top_k: 6 }" in app_js
    assert "function renderReaderQa()" in app_js
    assert "function sendReaderQa(text)" in app_js
    assert "data-reader-cite=" in app_js
    assert "jumpToSource(source.document_id, source.section_seq)" in app_js
    assert ".reader-panes.qa-mode" in styles
    assert ".reader-chat-panel" in styles


def test_web_ui_declares_every_workbench_screen():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    screens = set(re.findall(r'data-screen="([a-z]+)"', index))
    nav_keys = set(re.findall(
        r"\{ key: '([a-z]+)', label: '[^']+', sub: '[^']+', group: '[^']+' \}",
        app_js,
    ))

    assert screens == {"search", "journals", "library", "tags", "glossary", "reader", "chat", "chemistry"}
    assert nav_keys == screens, "每个导航项都必须有对应的画面，否则点了会切到空白"


def test_web_ui_navigation_has_no_count_badges():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "const badges" not in app_js
    assert 'class="badge"' not in app_js


def test_web_ui_navigation_groups_usage_before_management():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert "{ key: 'use', label: '功能' }" in app_js
    assert "{ key: 'manage', label: '管理' }" in app_js
    assert "group: 'use'" in app_js
    assert "group: 'manage'" in app_js
    assert app_js.index("key: 'search'") < app_js.index("key: 'journals'")
    assert app_js.index("key: 'chemistry'") < app_js.index("key: 'journals'")
    assert 'class="nav-group-title"' in app_js
    assert ".nav-group + .nav-group" in styles


def test_web_ui_can_create_whitelist_journal_from_left_navigation():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "{ key: 'journals', label: '期刊管理', sub: 'JOURNALS', group: 'manage' }" in app_js
    assert 'data-screen="journals"' in index
    assert '<div class="screen-title">期刊管理</div>' in index
    assert '<span class="chips-label">期刊</span>' in index
    assert 'id="journal-create-form"' in index
    assert 'id="journal-manager-list"' in index
    assert "function journalFormPayload()" in app_js
    assert "async function saveJournalFromWorkbench()" in app_js
    assert "api('/journals', { method: 'POST', body: payload })" in app_js
    assert "await loadJournals()" in app_js
    assert "bindJournals();" in app_js


def test_web_ui_whitelist_journals_can_be_edited_and_soft_deleted():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="journal-form-title"' in index
    assert 'id="journal-form-description"' in index
    assert "function editJournalFromWorkbench(journalId)" in app_js
    assert "async function deleteJournalFromWorkbench(journalId)" in app_js
    assert 'data-journal-edit="${journal.id}"' in app_js
    assert 'data-journal-delete="${journal.id}"' in app_js
    assert "method: 'PUT'" in app_js
    assert "method: 'DELETE'" in app_js
    assert "window.confirm" in app_js
    assert "已抓取的论文和历史任务不会删除" in app_js


def test_web_ui_whitelist_form_only_guards_journal_scope_fields():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    for control_id in (
        "journal-name",
        "journal-issn-print",
        "journal-issn-electronic",
        "journal-year-from",
        "journal-year-to",
    ):
        assert f'id="{control_id}"' in index
    assert 'id="journal-keywords"' not in index
    assert 'id="journal-keyword-mode"' not in index
    assert "请至少填写一个 Print ISSN 或 Electronic ISSN" in app_js
    assert "请至少填写一个主题关键词" not in app_js
    assert "白名单中已存在" in app_js
    assert "keywords: []" in app_js


def test_web_ui_search_defaults_to_relevance_with_bounded_result_count():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert '<option value="relevance" selected>按相关度</option>' in index
    assert "sort: 'relevance'" in app_js
    assert "resultLimit: 50" in app_js
    assert '<option value="50" selected>最多 50 篇</option>' in index
    assert 'id="save-search-batch"' in index
    assert 'id="discard-search-batch"' in index
    assert "params.set('search_id', state.activeSearchId)" in app_js
    assert "/crawl/searches/${state.activeSearchId}/save" in app_js
    assert "method: 'DELETE'" in app_js
    assert "撤销已保存批次" in app_js
    assert ".search-batch-actions[hidden] { display: none; }" in (
        WEB_DIR / "styles.css"
    ).read_text(encoding="utf-8")


def test_web_ui_tagging_writes_manual_category_override():
    """打标复用既有 taxonomy，不新增端点、不动 schema。"""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "/papers/${paperId}/categories" in app_js
    assert "method: 'manual'" in app_js
    assert "/categories" in app_js


def test_web_ui_has_unified_tag_manager_with_confirmed_delete():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'data-screen="tags"' in index
    assert 'id="tag-create-form"' in index
    assert 'id="tag-manager-list"' in index
    assert "async function deleteCategory(categoryId)" in app_js
    assert "window.confirm" in app_js
    assert "method: 'DELETE'" in app_js
    assert "result.removed_paper_links" in app_js


def test_web_ui_reader_and_chat_filter_real_documents_by_category():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="reader-category"' in index
    assert 'id="chat-category"' in index
    assert "function documentMatchesCategory(doc, slug)" in app_js
    assert "pool.filter((doc) => documentMatchesCategory(doc, state.readerCategory))" in app_js
    assert "doc.index_status === 'indexed' && documentMatchesCategory(doc, state.chatCategory)" in app_js
    assert "if (state.chatCategory) params.set('category', state.chatCategory)" in app_js


def test_web_ui_tag_manager_supports_inline_edit_and_cache_migration():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'data-category-edit="${category.id}"' in app_js
    assert 'data-category-edit-form="${category.id}"' in app_js
    assert "api(`/categories/${categoryId}`" in app_js
    assert "method: 'PUT'" in app_js
    assert "updateCategoryOnPaper(paper, updated, previous.slug)" in app_js
    assert "state.readerCategory = updated.slug" in app_js
    assert "state.chatCategory = updated.slug" in app_js
    assert ".tag-manager-row.is-editing" in styles


def test_web_ui_glossary_manager_persists_crud_in_local_workbench_state():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert "{ key: 'glossary', label: '术语表管理', sub: 'GLOSSARY', group: 'manage' }" in app_js
    assert 'data-screen="glossary"' in index
    assert 'id="glossary-form"' in index
    assert 'id="glossary-en"' in index
    assert 'id="glossary-zh"' in index
    assert 'id="glossary-manager-list"' in index
    assert "persisted.glossaryTerms = normalizeGlossaryTerms" in app_js
    assert "function saveGlossaryTerm()" in app_js
    assert "function deleteGlossaryTerm(id)" in app_js
    assert "saveStore();" in app_js
    assert 'class="glossary-column-head"' in index
    assert "<span>EN</span>" in index
    assert "<span>中文</span>" in index
    assert "glossary-language-mark" not in app_js
    assert "glossary-pair-arrow" not in app_js
    assert ".glossary-manager-row" in styles


def test_web_ui_reader_selection_offers_glossary_and_chat_actions():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    styles = (WEB_DIR / "styles.css").read_text(encoding="utf-8")

    assert 'id="selection-popover"' in index
    assert 'data-selection-action="glossary"' in index
    assert 'data-selection-action="chat"' in index
    assert "function showSelectionPopover(pane)" in app_js
    assert "function addSelectionToGlossary()" in app_js
    assert "function sendTextToChat(text, kind)" in app_js
    assert 'data-glossary-send="${g ? esc(g.id) : \'\'}"' in app_js
    assert ".selection-popover" in styles
    assert ".selection-popover[hidden]" in styles
    assert "id=\"sel-btn\"" not in index


def test_web_ui_prompt_presets_use_sql_api_for_full_crud():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    for control_id in (
        "new-preset",
        "preset-editor",
        "preset-cmd",
        "preset-desc",
        "preset-question",
        "cancel-preset",
    ):
        assert f'id="{control_id}"' in index
    assert "async function loadPresets()" in app_js
    assert "api('/prompt-presets?page_size=100')" in app_js
    assert "async function savePresetEditor()" in app_js
    assert "editing ? 'PUT' : 'POST'" in app_js
    assert "async function deletePreset(id)" in app_js
    assert "method: 'DELETE'" in app_js
    assert "state.presets = state.presets.filter" in app_js
    assert 'data-preset-edit="${esc(p.id)}"' in app_js
    assert 'data-preset-delete="${esc(p.id)}"' in app_js
    assert "persisted.customPresets.push" not in app_js
    assert "PRESETS.concat" not in app_js


def test_web_ui_prompt_preset_validation_and_legacy_migration():
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "发送内容不能为空" in app_js
    assert "不能包含空格" in app_js
    assert "快捷指令 ${cmd} 已存在" in app_js
    assert "async function migrateLegacyPromptPresets()" in app_js
    assert "delete persisted.customPresets" in app_js
    assert "maxlength=\"24\"" in (WEB_DIR / "index.html").read_text(encoding="utf-8")
    assert "maxlength=\"1000\"" in (WEB_DIR / "index.html").read_text(encoding="utf-8")


def test_web_ui_surfaces_reaction_export_gate_conflict():
    """导出闸门是红线：409 必须让用户看懂，而不是静默失败。"""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "e.status === 409" in app_js
    assert "reaction-sets/${state.chemSetId}/export" in app_js


def test_web_ui_self_attributes_reviews_without_reviewer_input():
    """单用户工作台无需填写复核人，但审计记录仍有稳定责任标识。"""
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="reviewer"' not in index
    assert ">复核人<" not in index
    assert "const SELF_REVIEWER = 'self';" in app_js
    assert "verified_by: SELF_REVIEWER" in app_js
    assert "reviewerDisplayName(a.verified_by)" in app_js
    assert "verified_by: persisted.reviewer.trim()" not in app_js
    assert "if (!persisted.reviewer.trim())" not in app_js


def test_web_ui_does_not_convert_rate_values():
    """速率系数保留论文原文，前端不得做单位换算。"""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    rate_line = next(line for line in app_js.split("\n") if "data-f=\"rate_value\"" in line)
    assert "esc(r.rate_value || '')" in rate_line
    for forbidden in ("parseFloat(payload.rate_value", "Number(payload.rate_value", "* 1e", "toExponential"):
        assert forbidden not in app_js


# ── 跨平台（mac 开发 → Windows 部署） ──

def test_app_runtime_never_relies_on_locale_default_encoding():
    """Windows 的默认 ANSI 代码页会把中文文本解成乱码，文件 IO 必须显式 utf-8。"""
    offenders = []
    for path in sorted((Path(__file__).resolve().parent.parent / "app").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
            if re.search(r"\.(read_text|write_text)\(", line) and "encoding=" not in line:
                offenders.append(f"{path.name}:{number}")
            if re.search(r"\bopen\(", line) and "encoding=" not in line and '"rb"' not in line and "'rb'" not in line:
                offenders.append(f"{path.name}:{number}")

    assert offenders == [], f"缺少显式 encoding，Windows 上会乱码：{offenders}"


def test_app_runtime_has_no_posix_only_dependencies():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((Path(__file__).resolve().parent.parent / "app").rglob("*.py"))
    )
    for posix_only in ("import fcntl", "import pwd", "import grp", "os.uname", "os.fork", "SIGKILL", "/dev/null"):
        assert posix_only not in sources, f"{posix_only} 在 Windows 上不可用"


def test_windows_launcher_exists_and_targets_windows_paths():
    launcher = (Path(__file__).resolve().parent.parent / "start.ps1").read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in launcher, "Windows venv 解释器不在 .venv/bin"
    assert ".venv/bin/python" not in launcher
    # 中文 Windows 默认 GBK：不锁 UTF-8 会让日志与 .env 乱码
    assert "PYTHONUTF8" in launcher
    assert "PYTHONIOENCODING" in launcher


def test_windows_launcher_honours_same_env_contract_as_start_sh():
    root = Path(__file__).resolve().parent.parent
    launcher = (root / "start.ps1").read_text(encoding="utf-8")
    shell = (root / "start.sh").read_text(encoding="utf-8")

    shared = [
        "API_HOST", "API_PORT", "STREAMLIT_HOST", "STREAMLIT_PORT", "API_BASE_URL",
        "DEV_READY_TIMEOUT", "DEV_EXIT_AFTER_READY", "START_OPEN_BROWSER",
        "PAPER_LAB_SCHEDULER_ENABLED", "LOG_DIR",
    ]
    for name in shared:
        assert name in shell, f"{name} 不在 start.sh 中，测试假设已过期"
        assert name in launcher, f"start.ps1 缺少 start.sh 支持的 {name}"
    # 两个启动器都应把工作台作为主入口
    assert "WORKBENCH_URL" in shell
    assert "WORKBENCH_URL" in launcher
