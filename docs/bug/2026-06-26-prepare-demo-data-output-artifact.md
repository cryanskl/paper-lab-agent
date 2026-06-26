# scripts/prepare_demo_data.py 无法写出发布摘要 artifact

## 现象

`scripts/prepare_demo_data.py --summary-only --compact` 只能把演示摘要输出到 stdout。发布交接时需要把 demo readiness 摘要保存为 `out/demo-summary.json` 这类文件时，只能依赖 shell 重定向；脚本自身不会创建输出目录，也不能像 `scripts/export_openapi.py --output out/openapi.json` 一样直接生成稳定 artifact。

## 原因

`scripts/prepare_demo_data.py` 的 CLI 只提供 stdout 输出路径，没有 `--output` 参数和父目录创建逻辑。

## 修复

新增 `--output` 参数。未指定时保持原 stdout 行为；指定时创建父目录并把当前 full payload 或 `--summary-only` payload 写入目标 JSON 文件。

## 验证

先新增契约测试并确认红灯，再实现 `--output`。

- RED 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_can_write_summary_output_file -q` 失败，`scripts/prepare_demo_data.py` 不识别 `--output`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_api.py::test_prepare_demo_data_script_can_write_summary_output_file -q` 通过，`1 passed`。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_release_contracts.py::test_release_check_validates_prepare_demo_data_output_artifact -q` 通过，`1 passed`。
- 完整 gate：`bash scripts/release_check.sh` 通过，`722 passed`。
