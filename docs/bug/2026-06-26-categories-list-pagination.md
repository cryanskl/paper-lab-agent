# Categories list pagination ignored

## 现象

`GET /api/v1/categories?page=2&page_size=3` 返回 HTTP 200，但响应仍是第一页完整分类列表，`page` 固定为 `1`，`page_size` 固定为返回条目数。

## 原因

分类列表接口没有声明 `page` 和 `page_size` 查询参数，响应中的分页字段由硬编码值生成，没有按统一列表契约切片。

## 修复

`GET /categories` 接收 `page` 和 `page_size` 查询参数，默认 `page=1`、`page_size=20`。接口先序列化完整分类列表以保留 `children` 字段，再对平铺结果做分页切片，并返回真实的 `total/page/page_size`。

## 验证

- `.venv/bin/python -m pytest tests/test_api.py -k categories -q`

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
