# Doctor crashed on unreadable env file

## 现象

- 触发命令、接口或页面：运行 `python scripts/doctor.py --strict --compact` 或直接调用 `check_local_storage(project, env={})`，且项目目录中的 `.env` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：doctor 在读取 `.env` 时直接抛出底层异常，例如 `UnicodeDecodeError`，无法输出结构化预检报告。
- 期望结果：doctor 应把坏 `.env` 转成稳定的 local storage issue，继续使用默认/环境变量路径生成报告，方便新机器排障。

## 原因

- 根因：`scripts/doctor.py` 的 `env_with_file_values()` 直接调用 `env_path.read_text(encoding="utf-8")`，没有捕获读取或解码错误。
- 影响范围：Quick Start 预检、release gate strict doctor 阶段、`.env` 配置损坏时的故障定位。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：新增 `.env` 读取 helper，将 symlink/非普通路径和读取/解码失败统一转为 issues；`env_with_file_values()` 在 `.env` 有问题时不读取该文件，`check_local_storage()` 返回 `env_file_unreadable` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_reports_unreadable_env_file -q` 失败，`check_local_storage()` 抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_reports_unreadable_env_file tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_reads_env_file tests/test_release_contracts.py::test_doctor_script_local_storage_preflight_keeps_environment_override -q` 通过，`4 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_script and (local_storage or env_file or symlinked)"` 通过，`11 passed, 283 deselected`；`.venv/bin/python -m py_compile scripts/doctor.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`901 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `901 passed`。
