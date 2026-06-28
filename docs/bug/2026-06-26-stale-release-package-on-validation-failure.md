# 打包失败后旧 release package 未清理

## 现象

如果 `scripts/package_release_artifacts.py` 的输出路径已经存在旧 zip，再用缺失或无效的 artifact 目录执行打包，脚本会返回 `ok: false`，但旧 zip 仍留在输出路径。

## 原因

`package_release_artifacts()` 在 artifact validation 失败后直接返回失败报告，没有处理既有输出文件。发布交接时如果复用同一个 `out/paper-lab-agent-release.zip` 路径，调用者可能误拿上一轮生成的 stale package。

## 修复

当 artifact validation 失败时，先删除目标输出路径上的旧文件，再返回失败报告。成功路径保持原行为，仍只在 validation 通过后写入新 zip。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure -q` 失败，旧 zip 仍存在。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`742 passed`。
