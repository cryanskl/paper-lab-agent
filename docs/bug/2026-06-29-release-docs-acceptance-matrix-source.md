# Release docs omitted acceptance matrix source-match validation

## 现象

- 触发命令、接口或页面：阅读 `README.md` 或 `docs/release-checklist.md` 的 release artifact handoff 说明。
- 实际结果：文档只说明验收矩阵会做关键文本或 edited matrix 校验，没有明确说明 `release-acceptance-matrix.md` 必须与源文件 `docs/release-acceptance-matrix.md` 逐字一致。
- 期望结果：发布文档应准确描述 validator 的真实行为，让交接人员知道不能手工编辑导出的验收矩阵，必须从仓库源文件重新生成。

## 原因

- 根因：上一阶段增强了 `scripts/validate_release_artifacts.py` 的验收矩阵源文件一致性校验，但 release 文档契约测试没有要求 README 和 release checklist 同步描述该约束。
- 影响范围：发布交接说明、人工复核 release handoff artifact 时的判断依据、后续维护者对验收矩阵校验边界的理解。

## 修复

- 修改文件：`README.md`、`docs/release-checklist.md`、`tests/test_release_contracts.py`。
- 关键行为：release 文档现在明确说明导出的验收矩阵必须与 `docs/release-acceptance-matrix.md` 逐字一致；契约测试锁定该说明，防止后续文档再次退化。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_release_artifact_bundle -q` 失败，README 缺少 `与 docs/release-acceptance-matrix.md 逐字一致` 说明。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_release_artifact_bundle -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1253 passed。
