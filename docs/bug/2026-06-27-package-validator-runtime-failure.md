# Package release artifacts crashed on validator runtime failure

## 现象

- 触发命令、接口或页面：`scripts/package_release_artifacts.py --artifact-dir out/release --output out/paper-lab-agent-release.zip --compact` 调用 release artifact validator 时遇到运行时异常。
- 实际结果：`validate_release_artifacts()` 抛出的异常会直接穿透 `package_release_artifacts()`，CLI 非结构化崩溃；如果输出路径已有旧 zip，也不会走既有失败清理逻辑。
- 期望结果：打包脚本应返回结构化 `ok:false` report，报告 validator 运行失败原因，并删除旧 release package，避免 stale zip 被误用。

## 原因

- 根因：`scripts/package_release_artifacts.py` 只处理 validator 返回 `ok:false` 的报告，没有在 `validate_release_artifacts()` 调用边界捕获普通异常。
- 影响范围：release package 打包、发布交接 zip 生成、发布 gate 中 artifact 校验异常时的失败诊断。

## 修复

- 修改文件：`scripts/package_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：在 artifact validator 调用边界捕获异常，删除既有输出 zip，并返回 `release artifact validation failed: ...` 的结构化失败报告。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_validator_runtime_failure -q` 失败，当前实现直接抛出 `RuntimeError("manifest parser crashed")`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_validator_runtime_failure tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure tests/test_release_contracts.py::test_package_release_artifacts_reports_zip_write_failure tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`4 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `795 passed`。
