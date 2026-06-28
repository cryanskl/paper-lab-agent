# Requirements validator crashed on unreadable Python source

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且 `app/`、`scripts/` 或 `streamlit_app.py` 中存在不可读取或非 UTF-8 的 Python 源文件。
- 实际结果：validator 在扫描源码 import 时抛出 `UnicodeDecodeError` 或 `OSError` traceback。
- 期望结果：requirements 发布契约校验应返回稳定错误，指出不可读取的 Python source，并以非零状态退出。

## 原因

- 根因：`imported_top_level_modules()` 只捕获 `SyntaxError`，没有把源码读取或解码失败转换为 CLI 层错误。
- 影响范围：requirements 依赖声明校验；坏的源码文件会中断 release gate，而不是给出可修复的文件级错误。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在执行缺包、imported package、unpinned 和 duplicate 校验前扫描项目 Python 源文件；读取或解码失败时输出 `python source unreadable: ...`，返回 `1`，不再输出 traceback。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_reports_unreadable_python_source -q` 失败，当前实现输出 `UnicodeDecodeError` traceback。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_reports_unreadable_python_source -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "requirements_validator"` 通过，`11 passed, 299 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`917 passed`；`bash scripts/release_check.sh` 通过。
