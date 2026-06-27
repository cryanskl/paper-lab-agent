# Validate release package leaked zip read failures

## 现象

- 触发命令、接口或页面：`scripts/validate_release_package.py --package <zip>` 在打开或读取 release zip 时遇到文件系统读取错误。
- 实际结果：`zipfile.ZipFile()` 或 zip 读取阶段抛出的 `OSError` 直接冒泡，CLI 输出 traceback，而不是 release handoff 可消费的结构化失败报告。
- 期望结果：release package 读取失败时返回结构化 `ok:false` report，并说明 package unreadable。

## 原因

- 根因：`validate_release_package()` 只捕获 `zipfile.BadZipFile`，没有捕获打开 zip 或读取 zip 过程中可能出现的 `OSError`。

## 修复

- 关键行为：`validate_release_package()` 捕获 zip 打开、枚举和解压阶段的 `OSError`，追加 `release package unreadable` issue，并继续返回标准 report。
- 影响范围：只改变 release package 读取失败时的失败路径；坏 zip 格式仍保留 `release package invalid zip` 文案，正常 package 校验保持不变。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_zip_read_failure -q` 失败，当前实现直接抛出 `OSError`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_validate_release_package_reports_zip_read_failure -q` 通过，`1 passed`。
- 扩展验证：`.venv/bin/python -m pytest tests/test_release_contracts.py -q -k "validate_release_package"` 通过，`8 passed, 233 deselected`。
- 全量验证：`.venv/bin/python -m pytest -q` 通过，`791 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `791 passed`。
