# Build release handoff resolved artifact symlinks before validation

## 现象

- 触发命令、接口或页面：`python scripts/build_release_handoff.py --artifact-dir <symlink> --package out/paper-lab-agent-release.zip --compact`
- 实际结果：builder 在调用底层 release 脚本前先 `resolve()` artifact 路径，导致 symlink artifact dir 变成真实目录，底层 export 的 symlink 拒绝逻辑无法触发。
- 期望结果：builder 应把调用者传入的路径交给底层脚本，由底层统一执行 symlink/path-safety 校验。

## 原因

- 根因：`scripts/build_release_handoff.py` 在 orchestration 入口提前解析 `artifact_dir` 和 `package_path`，绕开了 `scripts/export_release_artifacts.py`、`scripts/package_release_artifacts.py` 和 `scripts/validate_release_package.py` 已有的 requested-path 检查。
- 影响范围：使用单命令 handoff 时，symlinked artifact dir 等路径安全边界可能与分步命令不一致。

## 修复

- 修改文件：`scripts/build_release_handoff.py`、`tests/test_release_contracts.py`
- 关键行为：builder 保留原始输入路径传给底层 release 脚本；失败报告优先透传底层报告里的 `artifact_dir` 或 `output_dir`，避免重新 resolve 掩盖 symlink 路径。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_preserves_artifact_symlink_for_export_rejection -q` -> `1 failed`，builder 继续进入 artifact validation。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_build_release_handoff_preserves_artifact_symlink_for_export_rejection -q` -> `1 passed`
- 完整 gate：`.venv/bin/python -m pytest -q` -> `1061 passed`
