# Package release artifacts leaked zip write failures

## 现象

- 触发命令、接口或页面：`scripts/package_release_artifacts.py --artifact-dir <dir> --output <zip>` 在 artifact 校验通过后写入 release zip 时遇到文件系统错误。
- 实际结果：`zipfile.ZipFile(..., mode="w")` 或归档写入阶段抛出的 `OSError` 直接冒泡，CLI 输出 traceback，而不是 release handoff 可消费的结构化失败报告。
- 期望结果：release package 写入失败时返回结构化 `ok:false` report，并删除可能存在的半成品 zip。

## 原因

- 根因：`package_release_artifacts()` 只在写 zip 前校验输出路径类型和父目录类型；真正创建输出目录、打开 zip、写入 artifact 的阶段没有捕获 `OSError`。

## 修复

- 关键行为：`package_release_artifacts()` 捕获输出目录创建和 zip 写入阶段的 `OSError`，删除可能存在的输出文件，并返回 `release package write failed` issue。
- 影响范围：只改变 release package 写入失败时的失败路径；正常 zip 包内容、校验逻辑和成功 report 保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_zip_write_failure -q` 失败，当前实现直接抛出 `OSError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_package_release_artifacts_reports_zip_write_failure -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "package_release_artifacts"` 通过，`11 passed, 229 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`790 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `790 passed`。
