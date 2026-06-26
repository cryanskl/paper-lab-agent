# 文档运行文件引用未纳入链接校验

## 现象

`scripts/validate_docs_links.py` 只校验反引号中的 Markdown 和 SQL 文件引用，文档里出现的 `scripts/*.py`、`scripts/*.sh`、`.github/workflows/*.yml` 和 `.env.example` 引用即使写错也不会在发布检查中失败。

## 原因

反引号文件引用的正则只匹配 `.md` 和 `.sql` 后缀，导致发布说明和运行手册中更常见的脚本、CI 和环境模板路径没有被纳入 docs link gate。

## 修复

扩展 `BACKTICK_FILE_RE`，把 `.py`、`.sh`、`.yml`、`.yaml` 和 `.example` 文件引用纳入校验，并修正已有 bug 记录中缺少 `scripts/` 前缀的脚本引用。

## 验证

新增 `test_docs_links_validator_reports_missing_backtick_runtime_file_reference` 覆盖运行文件引用缺失场景。完整验证以 `bash scripts/release_check.sh` 为准。

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
