# SQLite initialization followed symlinked database paths

## 现象

- 触发命令、接口或页面：应用启动、测试初始化或 `init_db()` 使用 `DATABASE_PATH`，且该路径是指向配置目录外数据库文件的 symlink。
- 实际结果：`sqlite3.connect()` 跟随 symlink，在目录外目标文件上初始化 schema 和写入数据。
- 期望结果：SQLite 数据库路径本身和父目录链不能包含项目控制外的 symlink；遇到 symlinked `DATABASE_PATH` 时启动/初始化失败，不能写出配置路径之外。

## 原因

- 根因：`app/db.py` 的 `connect()` 在调用 `sqlite3.connect(settings.database_path)` 前没有检查数据库路径或父目录链是否安全。
- 影响范围：数据库初始化、所有 API/脚本的数据读写、release/demo 数据落库路径可信度。

## 修复

- 修改文件：`app/db.py`、`tests/test_api.py`。
- 关键行为：连接 SQLite 前扫描数据库目标路径和父目录链；遇到 symlink 或非普通文件路径时抛出 `OSError`，并且不初始化 symlink 目标文件。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_init_db_rejects_symlinked_database_path -q` 失败，当前实现未抛错。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_init_db_rejects_symlinked_database_path tests/test_api.py::test_health_seed_and_search tests/test_api.py::test_system_status_reports_symlinked_storage_dir_not_writable tests/test_api.py::test_fixture_import_script_runs_from_repo_root -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `809 passed`。
