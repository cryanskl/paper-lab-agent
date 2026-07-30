# Release gate unset 后仍回退读取本地凭据

## 现象

- 触发命令、接口或页面：开发机 `.env` 已配置 OpenAlex 或 Unpaywall 凭据时运行全量测试或 `bash scripts/release_check.sh`
- 实际结果：离线 preflight 只产生部分配置 warning，测试期望的三个确定性 warning 数量漂移；失败断言还可能打印从 `.env` 读取的配置值。
- 期望结果：离线发布门禁必须显式覆盖本地外部凭据，不因开发机 `.env` 内容改变结果，也不能在失败输出中暴露凭据。

## 原因

- 根因：`OFFLINE_PREFLIGHT_ENV` 使用 `env -u KEY` 删除进程变量，但 Pydantic Settings 随后会继续从仓库 `.env` 读取同名值。
- 影响范围：本地 `.env` 已配置 `OPENALEX_API_KEY`、`OPENALEX_MAILTO`、`UNPAYWALL_EMAIL` 或 `LLM_API_KEY` 的开发机及发布验证。

## 修复

- 修改文件：`scripts/release_check.sh`、`tests/test_api.py`、`tests/test_release_contracts.py`、`README.md`、`docs/release-checklist.md`
- 关键行为：离线 preflight 通过 `KEY=` 显式传入空环境变量，以环境变量优先级覆盖 `.env`；pytest 使用 `env -u` 保留环境加载器测试的“变量不存在”语义，依赖缺省配置的测试自身显式隔离外部凭据。

## 验证

- RED 证据：`.venv/bin/python -m pytest -q` -> `7 failed, 1286 passed`，发布 artifact 的 `preflight_warning_count` 在已配置开发机上从预期 `3` 变为 `1`。
- GREEN 证据：相关 7 个失败用例复测 -> `7 passed`。
- 后续回归：启用真实 Qwen 配置后又暴露 2 个子进程环境隔离遗漏，完整 gate 首次复跑为 `2 failed, 1294 passed`；两个用例显式隔离外部凭据后复测为 `2 passed`。
- 完整 gate：`bash scripts/release_check.sh` -> `1296 passed`。
