# Requirements validator followed symlinked Python source

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且 `app/`、`scripts/` 或 `streamlit_app.py` 中存在指向仓库外文件的 Python source symlink。
- 实际结果：validator 跟随 symlink 读取目标文件并继续 import 扫描；如果目标内容只导入标准库，校验可能返回成功。
- 期望结果：requirements 发布契约校验应拒绝 symlinked Python source，避免依赖扫描基于仓库外源码。

## 原因

- 根因：`python_files()` 使用 `Path.is_file()` 收集源码文件，`is_file()` 会跟随 symlink；后续读取和 AST 解析没有检查 source path 自身是否为 symlink。
- 影响范围：requirements 依赖声明校验；发布 gate 可能读取仓库边界外源码来证明当前 checkout 的依赖完整性。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在读取和解析 Python source 前检查源码路径自身；遇到 symlink 或非普通文件时输出 `python source is not a regular file: ...`，返回 `1`，不再继续读取目标。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source -q` 失败，当前实现返回 `0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "requirements_validator"` 通过，`13 passed, 299 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`919 passed`；`bash scripts/release_check.sh` 通过。
