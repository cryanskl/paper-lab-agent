# Streamlit empty chemistry tab requests reaction set 1

## 现象

在临时空数据目录启动 `bash scripts/dev.sh` 并打开 Streamlit 后，页面初始化过程中会请求 `GET /api/v1/reaction-sets/1`，API 返回 404。

这会让空库首次打开页面时产生不必要的错误请求。

## 原因

化学库 tab 在没有已加载反应集、也没有可选文档反应集时，仍会把 `reaction_set_id` number input 默认值设为 `1`，并因为 `reaction_set_detail` 不在 session state 中而自动加载 `/reaction-sets/1`。

## 修复

已修复。化学库 tab 现在只在用户点击“加载反应集”或从文档反应集列表选中有效 `reaction_set_id` 后请求详情，不再因为 `reaction_set_detail` 缺失而自动加载默认 ID 1。

## 验证

发现于 UI 验证：临时数据目录启动服务后打开 `http://127.0.0.1:8622`，FastAPI 日志出现 `GET /api/v1/reaction-sets/1` `404 Not Found`。

RED：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_does_not_auto_load_missing_reaction_set -q` 在修复前失败。

GREEN：`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_chemistry_tab_does_not_auto_load_missing_reaction_set -q`
