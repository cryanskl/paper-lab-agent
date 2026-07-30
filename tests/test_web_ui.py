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


def test_web_ui_separates_local_search_from_online_sync():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert 'id="do-search">检索本地库</button>' in index
    assert 'id="do-online-search">在线同步并检索</button>' in index
    assert "async function runOnlineSearch()" in app_js
    assert "api('/crawl/run', { method: 'POST', body })" in app_js
    assert "search_query: query" in app_js
    assert "await waitForCrawlJobs(jobIds)" in app_js
    assert "await runSearch(true, { keepSyncSummary: true })" in app_js


def test_web_ui_declares_every_workbench_screen():
    index = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    screens = set(re.findall(r'data-screen="([a-z]+)"', index))
    nav_keys = set(re.findall(r"\{ key: '([a-z]+)'", app_js))

    assert screens == {"search", "library", "reader", "chat", "chemistry"}
    assert nav_keys == screens, "每个导航项都必须有对应的画面，否则点了会切到空白"


def test_web_ui_tagging_writes_manual_category_override():
    """打标复用既有 taxonomy，不新增端点、不动 schema。"""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "/papers/${paperId}/categories" in app_js
    assert "method: 'manual'" in app_js
    assert "/categories" in app_js


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


def test_web_ui_requires_reviewer_before_verifying():
    """verified_by 必填——每次复核都要有可追溯责任人。"""
    app_js = (WEB_DIR / "app.js").read_text(encoding="utf-8")

    assert "verified_by: persisted.reviewer.trim()" in app_js
    assert "if (!persisted.reviewer.trim())" in app_js


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
