# Doctor 预检误把注释或相似变量名当成 .env.example 配置

## 现象

`scripts/doctor.py` 通过字符串包含判断 `.env.example` 是否包含必需配置键。这样 `MY_OPENALEX_MAILTO=` 或注释行 `# UNPAYWALL_EMAIL=` 也会被误判为已经配置，导致新机器预检漏报缺失的运行配置。

## 原因

doctor 没有按 `.env` 行语义解析 key，只检查 `f"{key}=" in text`。这个判断无法区分精确变量名、相似变量名和注释内容。

## 修复

新增 `env_example_keys`，按有效行解析 `.env.example`：跳过空行和注释，支持 `export KEY=value`，只接受符合环境变量命名规则的精确 key。`check_env_example` 改为基于解析后的 key 集合判断缺失项。

## 验证

先新增契约测试并确认红灯，再改 doctor 的 key 解析逻辑。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_ignores_comments_and_similar_key_names -q` 失败，doctor 未报告缺失的 `OPENALEX_MAILTO` 和 `UNPAYWALL_EMAIL`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_doctor_env_example_check_ignores_comments_and_similar_key_names -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py -k doctor -q` 通过，`9 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`711 passed`。
