# OpenAlex display_name title fallback was ignored

## 现象

- OpenAlex work payload 中 `title` 缺失或为空、但 `display_name` 仍包含论文标题时，客户端归一化结果会把 `title` 置为 `Untitled`。
- 这会让后续入库、FTS 检索和前端展示丢失真实标题。
- 期望结果：`title` 不可用时应回退使用非空字符串 `display_name`。

## 原因

- `OpenAlexClient.normalize_title` 只读取 `title` 字段。
- `OpenAlexClient.normalize` 没有把 OpenAlex work 的 `display_name` 传给标题归一化逻辑。

## 修复

- 修改文件：`app/clients/openalex.py`、`tests/test_clients.py`。
- 关键行为：`normalize_title` 增加可选 fallback；`normalize` 在 `title` 缺失时使用 `display_name`，并保留既有 `Untitled` 兜底。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_falls_back_to_display_name_for_missing_title -q` 失败，断言当前结果为 `Untitled`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_openalex_falls_back_to_display_name_for_missing_title tests/test_clients.py -q` 通过，`72 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`731 passed`。
