# Release artifact validator accepted edited acceptance matrix

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_release_artifacts.py --artifact-dir out/release --compact`，且 `release-acceptance-matrix.md` 被人工编辑后同步重算该文件和 `release-manifest.json` 的 checksum。
- 实际结果：validator 返回 `ok:true`，`issues:[]`，只确认 handoff 目录内部 checksum 自洽。
- 期望结果：validator 应拒绝与仓库源文件 `docs/release-acceptance-matrix.md` 不一致的验收矩阵，避免手工改动后的交接材料通过发布校验。

## 原因

- 根因：`validate_release_artifacts()` 只校验导出矩阵包含若干关键文本，并用 manifest checksum 校验包内自洽；它没有把导出文件内容和仓库源验收矩阵逐字比较。
- 影响范围：release artifact 校验、single-command handoff 的最终复验、对 PRD/schema/release gate 覆盖证据的交接可信度。

## 修复

- 修改文件：`scripts/validate_release_artifacts.py`、`tests/test_release_contracts.py`。
- 关键行为：validator 现在读取 `docs/release-acceptance-matrix.md`，要求导出的 `release-acceptance-matrix.md` 与源文件逐字一致；不一致时返回 `release acceptance matrix does not match docs/release-acceptance-matrix.md`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_acceptance_matrix_source_drift -q` 失败，validator 返回码为 `0` 且 `issues:[]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_artifacts_rejects_acceptance_matrix_source_drift tests/test_release_contracts.py::test_validate_release_artifacts_script_accepts_handoff_bundle -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1253 passed。
