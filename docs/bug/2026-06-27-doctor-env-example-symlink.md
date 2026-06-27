# Doctor followed symlinked env example

## 现象

- 触发命令、接口或页面：直接调用 `check_env_example(repo)`，且 `.env.example` 是指向仓库外文件的符号链接。
- 实际结果：doctor 跟随 symlink 读取目标文件；如果目标内容有效，`env_example` 检查会返回 `pass`。
- 期望结果：`.env.example` 应是仓库内普通文件；doctor 直调检查也应返回结构化失败，避免 Quick Start / release 预检读取仓库外配置样本。

## 原因

- 根因：`scripts/doctor.py` 的 `check_env_example()` 只判断 `path.exists() and path.is_file()`，该组合会跟随 symlink，未在读取前拒绝 `.env.example` 自身是 symlink 的情况。
- 影响范围：doctor 的 `.env.example` 配置契约检查；完整 doctor 入口已有 required-files 检查，但函数级直调仍可能放过 symlink。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：新增 `.env.example` regular-file 检查，在读取文件前拒绝 symlink 或非普通文件，并返回 `env_example_not_regular` issue；缺失 `.env.example` 的既有行为保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_rejects_symlinked_env_example -q` 失败，`check["status"]` 实际为 `pass`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_env_example"` 通过，`9 passed, 287 deselected`；`.venv/bin/python -m py_compile scripts/doctor.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`903 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `903 passed`。
