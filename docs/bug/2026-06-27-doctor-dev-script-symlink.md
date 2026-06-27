# Doctor followed symlinked dev script

## 现象

- 触发命令、接口或页面：直接调用 `check_env_example(repo)`，且 `scripts/dev.sh` 是指向仓库外文件的 symlink。
- 实际结果：doctor 跟随 symlink 读取目标文件，并可能返回 `pass`。
- 期望结果：doctor 应拒绝 symlinked dev script，避免 `.env.example` runtime 默认值检查基于仓库外脚本。

## 原因

- 根因：`dev_ready_timeout_runtime_issue()` 调用 `dev_ready_timeout_default()` 前没有检查 `scripts/dev.sh` 路径自身是否为 symlink 或非普通文件。
- 影响范围：Quick Start 预检和 release gate 中的 doctor 检查；直接调用 `check_env_example()` 时可能使用仓库外 `scripts/dev.sh` 作为 runtime 默认值真相源。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`
- 关键行为：读取 dev script 默认值前先拒绝 symlink 或非普通文件，返回 `dev_script_not_regular` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_symlinked_dev_script -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_symlinked_dev_script -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`11 passed, 304 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`922 passed`；`bash scripts/release_check.sh` 通过。
