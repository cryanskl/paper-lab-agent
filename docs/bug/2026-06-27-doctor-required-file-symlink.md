# Doctor preflight accepted symlinked required project files

## 现象

- 触发命令、接口或页面：`python scripts/doctor.py --strict --compact` 或 `check_required_files()` 检查项目必需文件，且 `README.md`、`requirements.txt`、`streamlit_app.py` 等必需文件是指向仓库外文件的 symlink。
- 实际结果：doctor 使用 `Path.is_file()` 判断必需文件存在；该判断会跟随 symlink，导致 symlinked required file 被当作普通文件接受。
- 期望结果：发布预检应拒绝 symlinked required project files，避免把仓库外文件误判为项目自身发布材料。

## 原因

- 根因：`scripts/doctor.py` 的 `check_required_files()` 没有在 `path.exists()` / `path.is_file()` 前检查 `path.is_symlink()`。
- 影响范围：release preflight、本地环境诊断、发布前项目文件完整性检查。

## 修复

- 修改文件：`scripts/doctor.py`、`tests/test_release_contracts.py`。
- 关键行为：required files 检查将 `path.is_symlink()` 视为无效，沿用 `missing_required_file` issue，避免 symlinked required file 通过 doctor。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_required_project_file -q` 失败，当前实现未报告 `README.md`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_required_project_file tests/test_release_contracts.py::test_doctor_script_reports_missing_required_project_files tests/test_release_contracts.py::test_doctor_env_example_check_matches_required_runtime_keys -q` 通过，`3 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `816 passed`。
