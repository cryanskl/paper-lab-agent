# Release package validator accepted non-file artifact entries

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_package.py --package <zip>`，且 zip 中某个 handoff artifact 条目的 Unix mode 标记为 FIFO、目录或其他非普通文件类型，但文件名和内容仍与合法 artifact 匹配。
- 实际结果：validator 只拒绝 symlink mode，未拒绝其他非普通文件 mode；Python 解压后仍能按普通文件读取内容，最终可能返回 `ok:true`。
- 期望结果：发布包内的 artifact 条目必须是普通文件；任何非普通文件 mode 都应在解压前返回 `ok:false` 并报告 `release package contains non-file artifact entries`。

## 原因

- 根因：`scripts/validate_release_package.py` 只扫描 `ZipInfo.external_attr` 中的 `stat.S_IFLNK`，没有把 FIFO、目录、socket、device 等其他非 regular file mode 纳入拒绝条件。
- 影响范围：release package 复验、handoff zip 来源边界、安全解压前的包结构可信度。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`。
- 关键行为：解压前扫描每个 zip artifact 条目的 Unix mode；除无 mode 信息、普通文件和已单独报告的 symlink 外，其他类型统一报告 `release package contains non-file artifact entries: [...]`，并停止后续解压验证。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_non_file_artifact_entry -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_non_file_artifact_entry tests/test_release_contracts.py::test_validate_release_package_rejects_symlink_artifact_entry -q` 通过，`2 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，1254 passed。
