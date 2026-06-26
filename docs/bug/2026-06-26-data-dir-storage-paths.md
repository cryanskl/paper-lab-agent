# PAPER_LAB_DATA_DIR 未派生本地存储路径

## 现象

使用临时目录启动 demo/API 时，如果只设置 `PAPER_LAB_DATA_DIR`，数据库、PDF、TEI、翻译、导出和本地向量索引路径仍可能落到默认 `data/...`，导致 `scripts/prepare_demo_data.py` 生成的数据和随后启动的 API/Streamlit 读取的数据目录不一致。

## 原因

`Settings` 中 `database_path`、`pdf_dir`、`tei_dir`、`translation_dir`、`export_dir` 和 `vector_db_path` 都有独立默认值。`PAPER_LAB_DATA_DIR` 改变后，这些字段没有在未显式配置时跟随新的 `data_dir` 重新派生。

## 修复

在配置加载阶段补充存储路径默认派生规则：当只配置 `PAPER_LAB_DATA_DIR` 时，本地存储默认落到该目录下；当显式配置 `DATABASE_PATH`、`PAPER_LAB_PDF_DIR` 或 `VECTOR_DB_PATH` 等字段时，显式值继续优先。

## 验证

新增 `tests/test_config.py` 覆盖 `PAPER_LAB_DATA_DIR` 默认派生和显式路径覆盖。完整验证以 `bash scripts/release_check.sh` 为准。

- 完整 gate：`bash scripts/release_check.sh` 通过，`708 passed`。
