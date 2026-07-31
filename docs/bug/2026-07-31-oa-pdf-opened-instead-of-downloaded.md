# OA PDF opened in a new tab instead of downloading

## 现象

- 触发命令、接口或页面：在 `/ui/` 的“待下载清单”点击单篇“下载”或“一键下载可用全文”。
- 实际结果：前端直接打开跨域 `oa_pdf_url`，出版商的内置 PDF 查看器接管页面，用户仍需手动点击保存；界面却提前显示“已发起”。
- 期望结果：点击后由系统获取并校验合法 OA PDF，浏览器直接保存文件；界面显示真实的下载中、已下载或失败状态。

## 原因

- 根因：`web/app.js` 的 `launchPaperDownload()` 创建带 `target=_blank` 的跨域链接；HTML `download` 属性无法覆盖出版商的 `Content-Disposition` 与跨域策略。
- 影响范围：待下载清单中的单篇和批量 OA 下载；元数据检索、闭源全文人工获取、PDF 上传及后续解析流程不受影响。

## 修复

- 修改文件：`docs/接口设计文档.md`、`app/services/oa_download.py`、`app/routers/papers.py`、`web/app.js`、`web/styles.css`、`scripts/validate_api_contract.py`、`scripts/validate_requirements.py`、`scripts/release_check.sh` 及对应测试。
- 关键行为：新增 `GET /papers/{id}/download` 附件响应；后端只读取已入库 OA URL，并校验公网 DNS、每次重定向、PDF 类型、100 MiB 上限和 `%PDF-` 签名。只转发当前浏览器 User-Agent，不转发 Cookie 或授权信息。前端通过同源 fetch 获取 Blob 后保存，并显示下载中、已下载或失败。

## 验证

- RED 证据：修复前 `launchPaperDownload()` 设置跨域 URL、`target=_blank` 和空 `download` 属性；真实页面点击后打开 IOP PDF 查看器而未直接保存。
- GREEN 证据：下载聚焦回归与契约测试 `.venv/bin/python -m pytest ... -q` -> `12 passed`；真实浏览器点击 IOP DOI `10.1088/2058-6272/ad5fe6` 后未打开新标签页，直接保存 10 页 PDF（`1474478` bytes，SHA-256 `0cce5714a145e0161e13f8435bdc4208e2e380a3d3ad88dec49cf7003c6ed090`），界面状态更新为“已下载”。
- 完整 gate：`.venv/bin/python -m pytest -q` -> `1329 passed, 6 failed`；其中 3 个既有 smoke 失败来自期刊关键词模式变更，1 个既有依赖失败来自其他未提交文件的 `starlette` 导入，本次引入的 2 个 OpenAPI 计数失败已修复并以发布聚焦回归 `4 passed` 复验。
