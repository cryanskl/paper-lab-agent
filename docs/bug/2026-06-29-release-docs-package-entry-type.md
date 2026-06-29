# Release docs omitted package artifact entry type validation

## 现象

- 触发命令、接口或页面：阅读 `README.md` 或 `docs/release-checklist.md` 的 release package 复验说明。
- 实际结果：文档只说明 release zip 会被解压和复验内容，没有明确说明 package validation 会在解压前拒绝 unsafe archive name、symlink artifact 和 non-file artifact entries。
- 期望结果：发布文档应准确描述 zip 复验的安全边界，让交接人员知道 release package 不只校验内容自洽，也校验 zip 条目类型。

## 原因

- 根因：上一阶段增强了 `scripts/validate_release_package.py` 的非普通文件 artifact 条目校验，但 README 和 release checklist 的契约说明没有同步更新。
- 影响范围：发布交接说明、人工复核 release zip 时的判断依据、后续维护者对 package validation 边界的理解。

## 修复

- 修改文件：`README.md`、`docs/release-checklist.md`、`tests/test_release_contracts.py`。
- 关键行为：release 文档现在明确说明 package validation 会拒绝 unsafe archive names、symlink artifacts 和 non-file artifact entries；契约测试锁定该说明。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_release_artifact_bundle -q` 失败，README 缺少 `zip 内 artifact 条目是否为普通文件` 说明。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_release_artifact_bundle -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1254 passed。
