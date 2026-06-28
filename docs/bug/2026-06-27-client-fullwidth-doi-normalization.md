# Academic clients did not normalize fullwidth DOI text

## 现象

- 触发命令、接口或页面：OpenAlex 或 Crossref 客户端归一化外部元数据时，`doi` / `DOI` 字段包含全角复制粘贴文本，例如 `ＤＯＩ：１０.５５５５／ＡＢＣ．Ｄｅｆ`。
- 实际结果：客户端直接 lower 和去前缀，无法识别全角 `ＤＯＩ：`、数字、斜杠和句点，输出 `ｄｏｉ：１０.５５５５／ａｂｃ．ｄｅｆ`。
- 期望结果：客户端输出进入 crawl 编排前就应稳定为半角 DOI `10.5555/abc.def`。

## 原因

- 根因：`app/clients/openalex.py` 和 `app/clients/crossref.py` 的 `normalize_doi()` 没有执行 Unicode `NFKC` 兼容归一化。
- 影响范围：确定性抓取层源头字段归一化、跨源 DOI 对齐、后续 Unpaywall 查询和入库去重诊断。

## 修复

- 修改文件：`app/clients/openalex.py`、`app/clients/crossref.py`、`tests/test_clients.py`。
- 关键行为：OpenAlex / Crossref 客户端在 DOI lower 和前缀移除前先执行 Unicode `NFKC` 归一化。

## 验证

- RED 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_normalizes_fullwidth_doi_text tests/test_clients.py::test_openalex_normalizes_fullwidth_doi_text -q` 失败，两个客户端都返回全角 lower 后的 DOI 字符串。
- GREEN 证据：`.venv/bin/python -m pytest tests/test_clients.py::test_crossref_normalizes_fullwidth_doi_text tests/test_clients.py::test_openalex_normalizes_fullwidth_doi_text -q` 通过，`2 passed`；`.venv/bin/python -m pytest tests/test_clients.py -q -k "doi"` 通过，`11 passed, 68 deselected`。
- 完整 gate：`.venv/bin/python -m pytest -q` 通过，`877 passed`；`bash scripts/release_check.sh` 通过，包含 `.venv/bin/python -m pytest -q` 的 `877 passed`。
