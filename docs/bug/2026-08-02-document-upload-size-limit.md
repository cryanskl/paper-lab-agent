# 手工 PDF 上传缺少体积上限

## 现象

`POST /api/v1/documents` 在校验 PDF 签名后调用无参数 `UploadFile.read()`，会把调用方提供的整个文件一次性读入 Python bytes。超大文件仍继续计算哈希、页数并尝试落盘和入库，接口没有 413 边界。

## 原因

OA 后台下载已有 100 MiB 限制，但手工 multipart 上传路径只验证扩展名、Content-Type 和 `%PDF-` 文件头，没有配置或读取上限。Starlette 的临时文件 spooling 不能替代应用层的内容大小约束。

## 修复

- Settings 新增 `MAX_PDF_UPLOAD_BYTES`，默认 104857600 bytes（100 MiB），允许配置 1–1073741824 bytes，并同步 `.env.example`、doctor 与接口文档。
- `save_upload()` 只读取“配置上限 + 1”字节；超过上限抛出专用异常，API 返回 `413 document_too_large`。
- 大小检查发生在 `save_document_bytes()` 之前，因此拒绝请求不会创建 PDF 文件或 document 记录。

## 验证

- RED：把测试上限设为 16 bytes 并上传更大的合法 PDF 头内容，旧接口返回 201。
- GREEN：同一请求返回 `413 document_too_large`，错误包含限制值，PDF 目录和 documents 表均为空；上传/流水线/翻译聚焦组 `26 passed`，配置契约组 `55 passed`。
- 完整 gate：`bash scripts/release_check.sh` 的 preflight、demo、health、package、smoke 全部通过；全量测试 `1424 passed, 5 warnings in 241.63s`。
