# Settings ensure_dirs followed symlinked data dir

## 现象

- 触发命令、接口或页面：`Settings.ensure_dirs()` 或任何会调用 `get_settings()` 的离线 demo、fixture、API 启动路径，且 `PAPER_LAB_DATA_DIR` 配置为 symlink 目录。
- 实际结果：配置层先执行 `mkdir(parents=True, exist_ok=True)`，可能在 symlink 目标目录下创建 `pdfs`、`tei`、`translations`、`exports` 等子目录，之后才由下游服务路径检查失败。
- 期望结果：配置层不应跟随 symlink 创建目录；诊断接口仍应能运行并报告坏路径，具体写入操作继续由服务级安全检查失败。

## 原因

- 根因：`app/config.py` 的 `Settings.ensure_dirs()` 只逐个调用 `path.mkdir(...)`，没有先检查目录路径本身或父级链是否包含 symlink。
- 影响范围：本地启动、fixture 导入、demo 数据准备、release gate 中的离线运行路径，以及新机器发布前的存储目录可信度。

## 修复

- 修改文件：`app/config.py`、`tests/test_config.py`、`tests/test_api.py`。
- 关键行为：`ensure_dirs()` 在创建目录前先检查目标目录和父级链；遇到 symlinked storage dir 或 symlinked parent 时跳过 `mkdir()`，不在 symlink 目标下创建子目录，并让下游诊断或服务级检查返回原有明确错误。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_config.py::test_ensure_dirs_rejects_symlinked_data_dir_before_creating_children -q` 失败，当前实现没有在创建目录前阻断 symlinked data dir。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_config.py::test_ensure_dirs_skips_symlinked_data_dir_before_creating_children tests/test_config.py -q` 通过，`5 passed`；受影响路径回归 `.venv/bin/python -m pytest tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable tests/test_api.py::test_document_upload_rejects_symlinked_pdf_storage_dir tests/test_api.py::test_parse_document_rejects_symlinked_tei_storage_dir tests/test_api.py::test_reaction_export_rejects_symlinked_output_parent tests/test_api.py::test_translate_document_rejects_symlinked_output_parent tests/test_api.py::test_rag_index_rejects_symlinked_vector_store_parent -q` 通过，`6 passed`；fixture/demo 扩展组通过，`10 passed`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`841 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `841 passed`。
