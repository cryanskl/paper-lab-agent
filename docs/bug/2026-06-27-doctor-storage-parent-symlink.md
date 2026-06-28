# Doctor preflight followed symlinked local storage parents

## 现象

- 触发命令、接口或页面：`python scripts/doctor.py --strict --compact` 或 `check_local_storage()` 检查本地存储路径，且 `PAPER_LAB_PDF_DIR`、`PAPER_LAB_TEI_DIR` 等目录位于 symlinked parent 之下。
- 实际结果：doctor 跟随父目录 symlink 创建缺失的存储子目录，继续写入 `.paper-lab-doctor-write-test` probe，并返回 `pass`。
- 期望结果：发布预检应拒绝 symlinked local storage parents，避免把 probe 或后续运行数据写到配置目录树之外。

## 原因

- 根因：`scripts/doctor.py` 的 `check_writable_directory()` 只拒绝目标路径本身是 symlink，未在 `path.mkdir(parents=True, exist_ok=True)` 前扫描父目录链。
- 影响范围：release preflight、本地环境诊断、发布前存储路径可信度。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：目录创建前扫描父目录链；遇到非系统根级 symlink parent 时返回 `storage_path_not_directory`，且不创建或写入 symlink 目标下的存储子目录。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_local_storage_parent -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_local_storage_parent tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_local_storage_dir tests/test_release_contracts.py::test_doctor_script_reports_local_storage_preflight_paths tests/test_release_contracts.py::test_doctor_script_reports_storage_parent_that_is_not_directory tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_reads_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_keeps_environment_override -q` 通过，`6 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `813 passed`。
