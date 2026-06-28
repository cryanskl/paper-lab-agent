# Doctor followed symlinked dev script parent

## 现象

- 触发命令、接口或页面：直接调用 `check_env_example(repo)`，且 `scripts/` 是指向仓库外目录的 symlink。
- 实际结果：doctor 跟随 symlinked parent 读取仓库外 `scripts/dev.sh`，并可能返回 `pass`。
- 期望结果：doctor 应拒绝 `scripts/dev.sh` 的 symlinked parent，避免 `.env.example` runtime 默认值检查基于仓库外启动脚本。

## 原因

- 根因：`dev_ready_timeout_runtime_issue()` 只拒绝 `scripts/dev.sh` 路径本身是 symlink 或非普通文件，没有在读取前扫描父级目录链。
- 影响范围：Quick Start 预检和 release gate 中的 doctor 检查；直接调用 `check_env_example()` 时可能使用仓库外 `scripts/dev.sh` 作为 runtime 默认值真相源。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`
- 关键行为：读取 dev script 默认值前先检查父目录链；发现 symlinked parent 时返回 `dev_script_parent_not_regular` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_symlinked_dev_script_parent -q` 失败，当前实现返回 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_symlinked_dev_script_parent -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`12 passed, 304 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`923 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `923 passed`。
