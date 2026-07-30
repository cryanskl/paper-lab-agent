# Invalid fixture PDF caused GROBID 500

## 现象

- 触发命令、接口或页面：在“文献库”中对 `fixture-plasma-chemistry.pdf` 执行 GROBID 解析。
- 实际结果：`POST http://127.0.0.1:8070/api/processFulltextDocument` 返回 HTTP 500；页面记录 `GROBID parse failed`，随后使用本地文本 fallback，并把 PDF 内部对象文本当作正文。
- 期望结果：演示 fixture 必须是标准、可渲染、可提取文本的 PDF；GROBID 应返回 TEI，解析结果不应依赖 fallback。

## 原因

- 根因：`app/fixture_loader.py` 的 fixture 只有 `%PDF-1.4`、一个不完整的 page object 和裸文本，共 181 字节，缺少页面树、内容流、xref、trailer 和 EOF 等标准 PDF 结构。
- 次生问题：修复 PDF 内容后 `file_hash` 会变化；旧 loader 只按新 hash 查重，会新增第二条 fixture 文档并保留旧错误记录及其章节、翻译、RAG 和化学派生产物。
- 影响范围：默认演示数据的 GROBID 解析、章节结构、翻译/RAG 引用质量、化学抽取，以及文献库页面对“已解析”状态的可信度。

## 修复

- 修改文件：`app/fixture_loader.py`、`requirements.txt`、`tests/test_fixture_pdf.py`。
- 关键行为：使用固定 metadata 和 invariant 模式的 ReportLab 生成确定性、单页、article-like 标准 PDF；通过 fixture DOI 和原文件名识别旧记录，内容变化时就地更新 `file_hash` 和路径，清理旧 sections、translations、chunks、reaction sets 与向量记录，并将下游状态重置为待处理。
- 真实链路：GROBID 0.9.0 对修复后的 PDF 返回 HTTP 200 和 TEI；`scripts/prepare_demo_data.py` 完成 5 个 sections、5 个 chunks、1 个 translation、1 个 verified reaction 和三种导出，`parse_error` 为空。
- 数据安全：更新本机演示数据前，已备份 `data/backups/plasma-before-grobid-fixture-fix-20260731.db` 和 `data/backups/vector-index-before-grobid-fixture-fix-20260731.json`。

## 验证

- RED 证据：旧 181 字节 fixture 真实 POST GROBID `/api/processFulltextDocument` 返回 HTTP 500，数据库 `documents.parse_error` 记录 `GROBID parse failed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_fixture_pdf.py tests/test_api.py::test_fixture_loader_imports_idempotent_document_sample tests/test_api.py::test_fixture_import_script_runs_from_repo_root tests/test_api.py::test_prepare_demo_data_script_populates_walking_skeleton -q` 通过，`5 passed`。
- PDF 证据：`pdfinfo` 报告 1 页、Letter、PDF 1.3、2418+ 字节；`pdftoppm` 渲染检查无裁切、重叠或不可读文本；`pypdf` 可打开并提取标题与反应式。
- 集成证据：GROBID 0.9.0 返回 HTTP 200、`application/xml` TEI；当前 `/api/v1/system/status?check_external=true` 返回 `grobid.available=true`、`status_code=200`，fixture 为 `parsed/indexed/extracted`、`parse_error=NULL`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `1298 passed`。
