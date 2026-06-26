# Release artifact validator 未拒绝额外文件

## 现象

`scripts/validate_release_artifacts.py` 只校验 `openapi.json`、`demo-summary.json` 和 `release-manifest.json` 是否存在且内容有效。如果 artifact 目录里混入旧摘要、临时文件或其他额外文件，validator 仍可能返回 `ok: true`。

## 原因

validator 只按固定文件名读取必需 artifact，没有检查目录顶层实际文件集合。发布交接时如果直接共享 artifact 目录而不是 zip，额外文件可能造成误用或泄露不应交付的内容。

## 修复

在 artifact validation 开始时检查目录顶层文件集合，只允许 `openapi.json`、`demo-summary.json` 和 `release-manifest.json`。发现额外文件时返回 `release artifact directory contains unexpected files` issue。同步更新 README 和 release checklist 的交接校验说明。

## 验证

先新增契约测试并确认红灯，再实现修复。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_unexpected_handoff_files -q` 失败，`report["issues"]` 为空。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_unexpected_handoff_files -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`744 passed`。
