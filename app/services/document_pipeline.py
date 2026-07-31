from typing import Any, Callable

from starlette.concurrency import run_in_threadpool

from app.services.chemistry import extract_reactions, mark_chemistry_queued
from app.services.documents import parse_document
from app.services.rag import index_document, mark_index_queued
from app.services.translation import create_translation_job, translate_document


async def run_document_pipeline(document_id: int, target_lang: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "document_id": document_id,
        "target_lang": target_lang,
        "status": "processing",
    }
    parsed = await parse_document(document_id)
    result["parse"] = parsed
    if parsed.get("parse_status") != "parsed":
        result["status"] = "failed"
        result["stopped_after"] = "parse"
        return result

    stages: list[tuple[str, Callable[..., dict], tuple[Any, ...]]] = []
    try:
        translation = create_translation_job(document_id, target_lang)
        stages.append(("translation", translate_document, (document_id, target_lang, translation["id"])))
    except Exception as exc:
        result["translation"] = {"status": "failed", "error": str(exc)}
    try:
        mark_index_queued(document_id)
        stages.append(("index", index_document, (document_id,)))
    except Exception as exc:
        result["index"] = {"status": "failed", "error": str(exc)}
    try:
        mark_chemistry_queued(document_id)
        stages.append(("chemistry", extract_reactions, (document_id,)))
    except Exception as exc:
        result["chemistry"] = {"status": "failed", "error": str(exc)}

    for name, operation, args in stages:
        try:
            result[name] = await run_in_threadpool(operation, *args)
        except Exception as exc:
            result[name] = {"status": "failed", "error": str(exc)}

    result["status"] = "done"
    return result
