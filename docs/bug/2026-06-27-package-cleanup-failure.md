# Package release artifacts crashed on stale package cleanup failure

## 现象

- 触发命令、接口或页面：`scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact` 在 validation 失败、validator 崩溃或 zip 写入失败后清理旧输出 zip。
- 实际结果：如果旧 `paper-lab-agent-release.zip` 删除失败，`Path.unlink()` 抛出的 `OSError` 会直接穿透，CLI 非结构化崩溃。
- 期望结果：旧 package 清理失败时返回结构化 `ok:false` report，明确指出 cleanup 失败原因，并避免调用方误以为已经清掉 stale zip。

## 原因

- 根因：`scripts/package_release_artifacts.py` 在多个失败分支直接调用 `output_path.unlink(missing_ok=True)`，没有捕获文件系统错误。
- 影响范围：release package 打包、发布交接 zip 生成失败后的清理可信度、发布 gate 的失败诊断。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：新增统一 cleanup helper；旧 package 删除失败时返回 `release package cleanup failed: ...` 的结构化失败报告，其他 validation 失败和 zip 写失败路径保持原有报告语义。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_stale_output_cleanup_failure -q` 失败，当前实现直接抛出 `OSError("permission denied")`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_stale_output_cleanup_failure tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_validator_runtime_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_zip_write_failure tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `797 passed`。
