# Release package validator accepted symlink artifact entries

## 现象

- 触发命令、接口或页面：运行 `scripts/validate_release_package.py --package <zip>`，且 zip 中某个 handoff artifact 条目的 Unix mode 标记为 symlink。
- 实际结果：validator 只检查 zip 条目名称和解压后的 artifact 内容；如果内容本身有效，会返回 `ok:true`。
- 期望结果：发布包内的 artifact 条目不能是 symlink；验证器应在解压前返回 `ok:false` 并报告 `release package contains symlink artifact entries`。

## 原因

`validate_release_package()` 检查了 artifact 名称是否匹配、重复和路径穿越，但没有读取 `ZipInfo.external_attr` 判断条目类型。带 symlink mode 的 zip 在部分解压器中可能还原为 symlink，不能作为可信发布 handoff 包。

## 修复

- 修改文件：`scripts/validate_release_package.py`、`tests/test_release_contracts.py`。
- 关键行为：解压前扫描 zip 条目的 Unix mode；命中 `stat.S_IFLNK` 时报告 `release package contains symlink artifact entries: [...]`，并停止后续解压验证。
- 影响范围：只改变含 symlink metadata 的 zip 包验证；普通 release package、Windows 路径穿越检测、tampered artifact 检测保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_symlink_artifact_entry -q` 失败，当前实现返回 `ok:true`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_rejects_symlink_artifact_entry tests/test_release_contracts.py::test_validate_release_package_rejects_windows_traversal_artifact_name tests/test_release_contracts.py::test_validate_release_package_rejects_windows_rooted_artifact_name tests/test_release_contracts.py::test_validate_release_package_script_rejects_tampered_zip_artifact tests/test_release_contracts.py::test_package_release_artifacts_script_writes_zip_bundle -q` 通过，`5 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1127 passed`。
