# Release package 输出路径可覆盖 artifact 文件

## 现象

`scripts/package_release_artifacts.py` 允许把 `--output` 指向 artifact 目录内部，例如 `out/release/openapi.json`。这种情况下打包流程可能返回 `ok: true`，同时覆盖或污染原本应该交付的 handoff artifact 文件。

## 原因

`package_release_artifacts()` 只在写 zip 前校验 artifact 目录本身有效，没有校验输出路径与 artifact 目录的包含关系。输出路径位于 artifact 目录内时，后续写入 zip 会和 handoff 文件集合发生冲突。

## 修复

在打包前拒绝 `output_path` 等于 artifact 目录或位于 artifact 目录内部的路径，并返回 `release package output must not be inside the artifact directory`。同步更新 README 和 release checklist，明确 zip 输出路径必须放在 artifact 目录外。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 失败，当前实现返回 `ok: true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_rejects_output_inside_artifact_dir -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle tests/test_release_contracts.py::test_package_release_artifacts_removes_stale_output_on_validation_failure -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`745 passed`。
