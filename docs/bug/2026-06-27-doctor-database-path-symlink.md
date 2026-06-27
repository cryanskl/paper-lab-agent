# Doctor preflight missed symlinked database paths

## 现象

- 触发命令、接口或页面：`python scripts/doctor.py --strict --compact` 或 `check_local_storage()` 检查本地存储路径，且 `DATABASE_PATH` 指向 symlinked SQLite 文件。
- 实际结果：doctor 只检查 `DATABASE_PATH` 的父目录可写，未检查数据库文件路径本身，导致预检返回 `pass`。
- 期望结果：发布预检应拒绝 symlinked `DATABASE_PATH`，避免发布前环境诊断把目录外数据库目标误判为可用。

## 原因

- 根因：`scripts/doctor.py` 的 `storage_path_config()` 只派生 `database_parent`，`check_local_storage()` 没有针对 `DATABASE_PATH` 文件路径本身做 symlink 或普通文件检查。
- 影响范围：release preflight、本地环境诊断、发布前数据库路径可信度。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：doctor 从同一套环境变量派生 `database_path`，对已存在但不是普通文件或本身是 symlink 的路径返回 `storage_path_not_file`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_database_path -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_database_path tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_local_storage_parent tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_local_storage_dir tests/test_release_contracts.py::test_doctor_script_reports_local_storage_preflight_paths tests/test_release_contracts.py::test_doctor_script_reports_storage_parent_that_is_not_directory tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_reads_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_keeps_environment_override -q` 通过，`7 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `814 passed`。
