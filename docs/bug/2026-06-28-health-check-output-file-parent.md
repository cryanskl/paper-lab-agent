# health_check output file parent reported generic write failure

## 现象

- 触发命令、接口或页面：`python scripts/health_check.py --base-url http://api.test --summary-only --compact --output <file-parent>/health-summary.json`，其中 `<file-parent>` 已存在且是普通文件。
- 实际结果：CLI 返回非零，但错误信息是泛化的 `failed to write output file ... Not a directory`，没有像其他发布工具一样明确指出输出父路径不是普通目录。
- 期望结果：CLI 应在写文件前拒绝已存在但不是目录的输出父路径，并返回 `output path parent is not a regular directory: <file-parent>`。

## 原因

- 根因：`scripts/health_check.py` 的 `write_output_file` 只检查输出文件 symlink、父级 symlink 和输出路径是否为普通文件，随后直接 `mkdir(parents=True)`；当父路径本身是普通文件时，只能从 `OSError` 生成泛化写入失败。
- 影响范围：发布前用 `--output out/health-summary.json` 写健康检查报告时，如果 `out` 被误创建为普通文件，排障信息不够明确。

## 修复

- 修改文件：`scripts/health_check.py`、`tests/test_api.py`
- 关键行为：`write_output_file` 在创建父目录前检查 `path.parent.exists() and not path.parent.is_dir()`，并返回明确的父路径错误；新增回归测试覆盖普通文件父路径。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_rejects_file_output_parent -q` -> `1 failed`，错误仍是 `failed to write output file ... Not a directory`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_health_check_rejects_file_output_parent tests/test_api.py::test_health_check_rejects_symlinked_output_parent tests/test_api.py::test_health_check_rejects_symlinked_output_file tests/test_api.py::test_health_check_can_write_summary_output_file -q` -> `4 passed`
- 完整 gate：`bash scripts/release_check.sh` -> `1098 passed`
