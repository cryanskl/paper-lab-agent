# Requirements validator followed symlinked source root

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_requirements.py`，且源码根目录之一（例如 `app`）是指向仓库外目录的 symlink。
- 实际结果：validator 没有拒绝该 source root，可能跟随仓库外目录扫描 import，或在没有扫描到文件时返回成功。
- 期望结果：requirements 发布契约校验应拒绝 symlinked Python source root，避免依赖扫描基于仓库外源码或不完整源码树。

## 原因

- 根因：`python_files()` 对 source root 只通过 `is_dir()` / `rglob()` 查找文件，没有在入口处检查 root path 自身是否为 symlink。
- 影响范围：requirements 依赖声明校验；发布 gate 可能基于仓库边界外的 source root 判断依赖完整性。

## 修复

- 修改文件：`scripts/validate_requirements.py`、`tests/test_release_contracts.py`
- 关键行为：主入口在读取和解析 Python source 前检查 `SOURCE_PATHS` 根路径；遇到 symlinked root 时输出 `python source root is not a regular directory: ...`，返回 `1`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source_root -q` 失败，当前实现返回 `0`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_requirements_validator_rejects_symlinked_python_source_root -q` 通过，`1 passed`；`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "requirements_validator"` 通过，`14 passed, 299 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`920 passed`；`bash scripts/release_check.sh` 通过。
