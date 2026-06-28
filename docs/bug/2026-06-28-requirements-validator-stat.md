# Requirements validator treated stat as a missing dependency

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且项目源码中导入 Python 标准库 `stat`。
- 实际结果：validator 返回 `requirements missing imported packages: stat`。
- 期望结果：`stat` 是 Python 标准库模块，不应要求写入 `requirements.txt`。

## 原因

`scripts/validate_requirements.py` 用 `FALLBACK_STDLIB_MODULES` 兜底识别标准库模块。当前运行环境下 `stat` 没有被自动标准库集合覆盖，而 fallback 列表也漏掉了 `stat`，导致它被当成第三方依赖。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`。
- 关键行为：把 `stat` 加入 `FALLBACK_STDLIB_MODULES`，并扩展标准库 import 回归测试。
- 影响范围：只改变 `stat` 的依赖分类；第三方导入缺失检测、直接必需依赖检测和其他标准库识别保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q` 失败，当前实现返回 `['stat']`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_symlink_artifact_entry tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1127 passed`。
