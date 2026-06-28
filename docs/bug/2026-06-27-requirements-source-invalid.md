# Requirements validator ignored invalid Python source

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且 `app/`、`scripts/` 或 `streamlit_app.py` 中存在 Python 语法错误的源码文件。
- 实际结果：validator 在扫描 import 时捕获 `SyntaxError` 后直接跳过该文件，最终可能返回成功。
- 期望结果：requirements 发布契约校验应把无效 Python source 作为稳定错误报告，并以非零状态退出。

## 原因

- 根因：`imported_top_level_modules()` 捕获 `SyntaxError` 后 `continue`，导致依赖扫描基于不完整源码继续执行。
- 影响范围：requirements 依赖声明校验；语法损坏的源码可能不参与 import 扫描，release gate 对依赖完整性的证明变弱。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在执行缺包、imported package、unpinned 和 duplicate 校验前解析项目 Python 源文件；语法错误时输出 `python source invalid: ...`，返回 `1`，不再静默跳过。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_reports_invalid_python_source -q` 失败，当前实现返回 `0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_reports_invalid_python_source -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "requirements_validator"` 通过，`12 passed, 299 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`918 passed`；`bash scripts/release_check.sh` 通过。
