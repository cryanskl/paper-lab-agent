# Doctor crashed on unreadable dev script

## 现象

- 触发命令、接口或页面：运行 `scripts/doctor.py` 或直接调用 `check_env_example(repo)`，且仓库内 `scripts/dev.sh` 存在但不可读取或不是 UTF-8 文本。
- 实际结果：doctor 在比对 `.env.example` 的 `DEV_READY_TIMEOUT` runtime 默认值时抛出 `UnicodeDecodeError` 或 `OSError`。
- 期望结果：doctor 应返回结构化失败 issue，指出 dev script 不可读，并继续保持 JSON 诊断输出。

## 原因

- 根因：`dev_ready_timeout_runtime_issue()` 直接调用 `dev_ready_timeout_default()`，后者读取 `scripts/dev.sh` 时没有把读取和解码失败转换为 doctor issue。
- 影响范围：Quick Start 预检和 release gate 中的 doctor 检查；坏的 dev script 会中断诊断流程，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`
- 关键行为：`dev_ready_timeout_runtime_issue()` 捕获 `OSError` 和 `UnicodeError`，返回 `dev_script_unreadable` issue，`check_env_example()` 将其纳入结构化失败结果。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_unreadable_dev_script -q` 失败，当前实现抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_reports_unreadable_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`10 passed, 304 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`921 passed`；`bash scripts/release_check.sh` 通过。
