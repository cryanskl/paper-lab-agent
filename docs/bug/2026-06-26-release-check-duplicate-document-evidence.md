# Release gate 未暴露重复上传复用原文档证据

## 现象

`scripts/smoke_check.py` 会在内部断言重复上传同一 PDF 返回的 `document.id` 等于首次上传的文档 ID，但 smoke summary 只返回 `duplicate_document_id`。`scripts/release_check.sh` 因此只能证明重复上传返回了某个 ID，无法从发布证据中证明它复用了原文档而不是创建了另一个文档。

## 原因

重复上传语义的校验停留在 smoke 脚本局部断言里，没有作为结构化 summary 字段输出；release gate 也没有期望这个布尔证据。

## 修复

新增 `duplicate_document_matches_original` smoke summary 字段，并在 `scripts/release_check.sh` 的期望 payload 中要求该字段为 `True`。同时新增契约测试，防止后续删除这条发布证据。

## 验证

先新增契约测试并确认红灯，再实现 smoke summary 与 release gate 断言。

- RED 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_requires_document_list_and_detail_smoke_paths -q` 失败，缺少 `"duplicate_document_matches_original": True`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_requires_document_list_and_detail_smoke_paths -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`716 passed`。
