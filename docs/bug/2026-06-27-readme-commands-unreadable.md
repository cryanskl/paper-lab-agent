# README command validator crashed on unreadable command doc

## 现象

- 触发命令、接口或页面：运行 `python scripts/validate_readme_commands.py` 或调用 `missing_command_targets(repo)`，且 `README.md` 或 release checklist 不是 UTF-8 文本或读取阶段抛出 `OSError`。
- 实际结果：校验器在提取 bash fenced block、inline command、script option 或 curl route 时抛出底层异常，例如 `UnicodeDecodeError` traceback。
- 期望结果：README command gate 应返回稳定 issue，指出命令文档不可读，而不是中断整个 release gate。

## 原因

- 根因：`scripts/validate_readme_commands.py` 的 `missing_command_targets_for_doc()` 在确认 command doc 不是 symlink 且是普通文件后，直接调用多个会读取该文档的解析函数；读取和解码错误没有转换为可诊断 issue。
- 影响范围：README 命令校验、release checklist 命令校验、release gate、CI 发布说明可运行性检查。

## 修复

- 修改文件：`scripts/validate_readme_commands.py`、`tests/test_release_contracts.py`。
- 关键行为：command doc regular-file 检查通过后、提取命令目标前，先用 UTF-8 读取文档；读取或解码失败时返回 `<label>: command doc unreadable` issue。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_readme_commands_validator_reports_unreadable_readme -q` 失败，函数抛出 `UnicodeDecodeError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "readme_commands"` 通过，`27 passed, 278 deselected`；`.venv/bin/python -m py_compile scripts/validate_readme_commands.py` 通过。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`912 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `912 passed`。
