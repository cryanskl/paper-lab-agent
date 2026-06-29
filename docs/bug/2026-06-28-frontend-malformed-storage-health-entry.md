# Frontend storage health display crashed on malformed entry

## 现象

- 触发命令、接口或页面：Streamlit 侧边栏渲染 `/api/v1/system/status.storage_health`，顶层对象存在，但某个健康项不是对象，例如 `{"database": "bad"}`。
- 实际结果：`storage_health_caption_rows()` 直接对该健康项调用 `.get(...)`，抛出 `AttributeError`，存储健康诊断无法继续显示。
- 期望结果：malformed storage health entry 应作为 `<key>: invalid` warning 展示，并继续渲染其它存储健康条目。

## 原因

- 根因：`storage_health_caption_rows()` 只校验了 `storage_health` 顶层必须是 dict，没有校验每个固定健康项的值也必须是 dict。
- 影响范围：Streamlit 系统侧边栏、异常 API 响应或接口契约漂移时的存储健康诊断信号。

## 修复

- 修改文件：`app/frontend_api.py`、`tests/test_frontend_api.py`。
- 关键行为：当 `data_dir`、`database`、`vector_db` 等存储健康项不是对象时，追加 `{"kind": "warning", "text": "<key>: invalid"}`，再按空对象继续输出缺省 caption，避免侧边栏中断。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_entries -q` 失败，报 `AttributeError: 'str' object has no attribute 'get'`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_entries tests/test_frontend_api.py::test_storage_health_caption_rows_include_parent_dirs_and_vector_json_state tests/test_frontend_api.py::test_storage_health_caption_rows_blocks_malformed_storage_health_object -q` 通过，`3 passed`；`.venv/bin/python -m pytest tests/test_frontend_api.py -q` 通过，`92 passed`；`.venv/bin/python -m pytest tests/test_api.py::test_streamlit_sidebar_surfaces_storage_health -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`1147 passed`。
