# Requirements validator flagged unicodedata as missing dependency

## 现象

- 触发命令、接口或页面：代码中新增 `import unicodedata` 后运行 `.venv/bin/python scripts/validate_requirements.py` 或 `bash scripts/release_check.sh`。
- 实际结果：validator 报错 `requirements missing imported packages: unicodedata`，把 Python 标准库误判为未声明的第三方依赖。
- 期望结果：`unicodedata` 属于 Python 标准库，不应要求写入 `requirements.txt`。

## 原因

- 根因：`scripts/validate_requirements.py` 在当前运行环境下依赖 `FALLBACK_STDLIB_MODULES` 识别标准库模块，该 fallback 列表漏掉了 `unicodedata`。
- 影响范围：任何新增 `unicodedata` import 的成品化改动都会被 release gate 误挡。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`。
- 关键行为：将 `unicodedata` 纳入 fallback 标准库模块集合，并在标准库忽略测试中覆盖该 import。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports -q` 失败，`missing` 实际为 `["unicodedata"]`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_ignores_standard_library_imports tests/test_release_contracts.py::test_requirements_validator_runs_as_release_script -q` 通过，`2 passed`；`.venv/bin/python scripts/validate_requirements.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`873 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `873 passed`。
