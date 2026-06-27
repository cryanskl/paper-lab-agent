# Doctor accepted symlinked env file

## 现象

- 触发命令、接口或页面：运行 `python scripts/doctor.py --strict --compact` 或直接调用 `check_local_storage(project, env={})`，且项目目录中的 `.env` 是指向仓库外文件的 symlink。
- 实际结果：doctor 的本地存储预检会跟随 symlink 读取仓库外 `.env`，使用其中的 `PAPER_LAB_DATA_DIR`、`DATABASE_PATH` 等配置派生和探测本地存储路径，并返回成功。
- 期望结果：doctor 作为 Quick Start 和 release gate 的预检入口，应拒绝 symlinked `.env`，不读取目标文件，并报告稳定的 local storage issue。

## 原因

- 根因：`scripts/doctor.py` 的 `env_with_file_values()` 只用 `exists()` 和 `is_file()` 判断 `.env`，而这两个检查会跟随指向普通文件的 symlink。
- 影响范围：新机器启动前预检、release gate 的 strict doctor 阶段、`.env` 驱动的本地存储路径可信度。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：新增 `.env` 输入安全检查；当 `.env` 是 symlink、非普通文件或父目录链包含 symlink 时，`check_local_storage()` 返回 `env_file_not_regular` 或 `env_file_parent_not_regular` issue，并且 `env_with_file_values()` 不读取该文件。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_env_file -q` 失败，`check_local_storage()` 实际返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_reads_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_keeps_environment_override -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_script and (local_storage or symlinked)"` 通过，`10 passed, 283 deselected`；`.venv/bin/python -m py_compile scripts/doctor.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`900 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `900 passed`。
