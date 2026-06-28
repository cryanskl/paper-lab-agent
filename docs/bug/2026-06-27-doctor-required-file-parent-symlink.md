# Doctor accepted required files through symlinked parent

## 现象

- 触发命令、接口或页面：运行 `python scripts/doctor.py --strict --compact` 或直接调用 `check_required_files()`，且必需项目文件位于 symlinked parent 下。
- 实际结果：doctor 会跟随父级 symlink，并把仓库外父目录中的 `docs/schema.sql` 等 required file 当作有效文件。
- 期望结果：doctor 的 required files 检查应只接受当前仓库普通文件树中的文件；遇到 symlinked parent 应将对应 required file 视为缺失或无效。

## 原因

- 根因：`check_required_files()` 只拒绝 required file 本身是 symlink 或非普通文件，没有检查父级目录链。
- 影响范围：P4 新机器预检和发布前排障可能把仓库边界外文件误判为当前 checkout 的必需文件。

## 修复

- 在 `scripts/doctor.py` 的 required files 检查中复用 `first_symlink_parent()`。
- 当 required file 路径任一父级目录是 symlink 时，沿用 `missing_required_file` issue，避免把仓库外文件当作本地 setup 证据。

## 验证

- RED：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_required_project_file_parent -q` 失败，当前实现未报告 `docs/schema.sql`。
- GREEN：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_required_project_file_parent tests/test_release_contracts.py::test_doctor_script_rejects_symlinked_required_project_file tests/test_release_contracts.py::test_doctor_script_reports_missing_required_project_files -q` 通过，`3 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "doctor_script"` 通过，`12 passed, 263 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`840 passed`；`bash scripts/release_check.sh` 通过。
