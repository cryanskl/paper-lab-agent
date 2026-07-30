# Requirements validator 把 io 误判为第三方依赖

## 现象

- 触发命令：`.venv/bin/python scripts/validate_requirements.py` 或 `bash scripts/release_check.sh`
- 实际结果：发布门禁报告 `requirements missing imported packages: io`。
- 期望结果：`io` 属于 Python 标准库，不应写入 `requirements.txt`。

## 原因

- 项目运行 Python 3.9，无法从 `sys.stdlib_module_names` 获得完整标准库集合。
- `scripts/validate_requirements.py` 的 `FALLBACK_STDLIB_MODULES` 漏掉了 `io`，而 `app/fixture_loader.py` 使用 `from io import BytesIO`。

## 修复

- 将 `io` 加入 fallback 标准库集合。
- 扩展标准库 import 回归测试，确保它不会再次被识别为第三方包。

## 验证

- RED 证据：`.venv/bin/python scripts/validate_requirements.py` 返回 1，并报告缺少 `io`。
- GREEN 证据：标准库识别用例与 requirements validator 复测通过。
- 完整 gate：`bash scripts/release_check.sh` -> `1296 passed`。
