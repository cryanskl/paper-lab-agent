# Release package path comparison used unresolved tempfile paths

## 现象

- 触发命令、接口或页面：`bash scripts/release_check.sh`
- 实际结果：release gate 在 package 报告校验处失败；`package["artifact_dir"]` 和 `package["package_path"]` 是 `/private/var/...`，而 gate 用未解析的 `/var/...` 临时路径比较。
- 期望结果：release gate 应按 package 脚本报告的 resolved path 形态比较本轮 `artifact_dir` 和 `package_path`。

## 原因

- 根因：`scripts/package_release_artifacts.py` 会对 artifact/output 路径执行 `resolve()` 后写入报告；`scripts/release_check.sh` 新增路径校验时使用了未 resolve 的 `output_dir` 和 `package_path`。
- 影响范围：macOS 上 `/var` 到 `/private/var` 这类路径别名会让 release gate 误判失败；实际发布包内容和校验和并未损坏。

## 修复

- 修改文件：`scripts/release_check.sh`、`tests/test_release_contracts.py`、`docs/release-checklist.md`
- 关键行为：release gate 改为比较 `str(output_dir.resolve())` 和 `str(package_path.resolve())`；合同测试固定 resolved path 期望；checklist 明确 package report 输出 resolved paths。

## 验证

- RED 证据：`bash scripts/release_check.sh` 失败，输出 `release_check failed: release artifact package=...`，其中报告路径为 `/private/var/...`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_release_artifact_bundle -q` -> `1 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1054 passed`
