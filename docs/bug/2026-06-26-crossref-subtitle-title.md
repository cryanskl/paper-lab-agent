# Crossref subtitle title fallback was ignored

## 现象

- Crossref work payload 中 `title` 为空列表或不可用、但 `subtitle` 有可用标题文本时，客户端归一化结果会把 `title` 置为 `Untitled`。
- 这会让通过 Crossref fallback 入库的论文丢失可检索标题，影响 FTS 检索和前端展示。
- 期望结果：`title` 不可用时应回退使用非空 `subtitle`，再兜底为 `Untitled`。

## 原因

- `CrossrefClient.normalize` 只调用 `first_text(item.get("title"), "Untitled")`。
- `subtitle` 字段没有参与标题归一化逻辑。

## 修复

- 修改文件：`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：标题归一化优先使用 `title`，缺失时使用 `subtitle`，最后才返回 `Untitled`。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_falls_back_to_subtitle_for_missing_title -q` 失败，断言当前结果为 `Untitled`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_falls_back_to_subtitle_for_missing_title tests/test_clients.py -q` 通过，`73 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`732 passed`。
