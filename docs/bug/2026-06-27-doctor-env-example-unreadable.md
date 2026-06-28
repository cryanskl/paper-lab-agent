# Doctor crashed on unreadable env example

## 现象

- 触发命令、接口或页面：运行 `python scripts/doctor.py --strict --compact` 或直接调用 `check_env_example(repo)`，且 `.env.example` 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：doctor 在解析 `.env.example` 时直接抛出底层异常，例如 `UnicodeDecodeError`，无法输出结构化预检报告。
- 期望结果：doctor 应把坏 `.env.example` 转成稳定的 `env_example` issue，让新机器或 release gate 能明确指出示例配置文件不可读。

## 原因

- 根因：`scripts/doctor.py` 的 `env_example_values()` 直接调用 `path.read_text(encoding="utf-8")`，没有捕获读取或解码错误。
- 影响范围：Quick Start 预检、release gate strict doctor 阶段、`.env.example` 配置契约检查。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：`env_example_values()` 现在返回 `(values, issue)`；读取或解码失败时返回 `env_example_unreadable` issue。`check_env_example()` 收到该 issue 后直接返回结构化失败报告，不继续执行缺失键、默认值或 runtime drift 检查。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_unreadable_env_example -q` 失败，`check_env_example()` 抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_unreadable_env_example tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys tests/test_release_contracts.py::test_doctor_env_example_check_rejects_secret_like_values tests/test_release_contracts.py::test_doctor_env_example_check_rejects_settings_default_drift -q` 通过，`4 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`8 passed, 287 deselected`；`.venv/bin/python -m py_compile scripts/doctor.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`902 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `902 passed`。
