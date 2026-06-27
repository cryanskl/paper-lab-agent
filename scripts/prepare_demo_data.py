#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configure_storage_defaults() -> None:
    data_dir = os.environ.get("PAPER_LAB_DATA_DIR")
    if not data_dir:
        return
    base = Path(data_dir)
    os.environ.setdefault("DATABASE_PATH", str(base / "plasma.db"))
    os.environ.setdefault("PAPER_LAB_PDF_DIR", str(base / "pdfs"))
    os.environ.setdefault("PAPER_LAB_TEI_DIR", str(base / "tei"))
    os.environ.setdefault("PAPER_LAB_TRANSLATION_DIR", str(base / "translations"))
    os.environ.setdefault("PAPER_LAB_EXPORT_DIR", str(base / "exports"))
    os.environ.setdefault("VECTOR_DB_PATH", str(base / "vector-index.json"))
    os.environ.setdefault("VECTOR_DB_BACKEND", "local-json")


def resource_counts(conn) -> dict[str, int]:
    tables = [
        "journals",
        "papers",
        "documents",
        "sections",
        "translations",
        "chunks",
        "reaction_sets",
        "reactions",
        "reaction_audits",
    ]
    return {
        table: conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        for table in tables
    }


def fixture_document_id(conn) -> int:
    row = conn.execute(
        """
        SELECT id
        FROM documents
        WHERE original_name='fixture-plasma-chemistry.pdf'
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()
    if not row:
        raise RuntimeError("fixture document was not imported")
    return int(row["id"])


def verify_all_reactions(reaction_set: dict, verified_by: str) -> dict:
    from app.services.chemistry import verify_reaction

    current = reaction_set
    for reaction in current.get("reactions") or []:
        current = verify_reaction(
            int(reaction["id"]),
            True,
            reaction.get("rate_value") or "fixture source value",
            verified_by,
            reaction_type=reaction.get("reaction_type")
            if reaction.get("reaction_type") not in {None, "", "unknown"}
            else "ionization",
            rate_type=reaction.get("rate_type")
            if reaction.get("rate_type") not in {None, "", "unknown"}
            else "cross_section",
            threshold_ev=reaction.get("threshold_ev"),
            cross_section_url=reaction.get("cross_section_url"),
        )
    return current


def demo_summary(
    document: dict,
    translation: dict,
    reaction_set: dict,
    exports: dict,
    counts: dict[str, int],
    demo_data: dict,
) -> dict:
    return {
        "ready": demo_data.get("ready") is True,
        "missing": demo_data.get("missing") or [],
        "document_id": document.get("id"),
        "parse_status": document.get("parse_status"),
        "index_status": document.get("index_status"),
        "chemistry_status": document.get("chemistry_status"),
        "translation_status": translation.get("status"),
        "reaction_set_id": reaction_set.get("id"),
        "reaction_set_status": reaction_set.get("status"),
        "reaction_set_verified_by": reaction_set.get("verified_by"),
        "reaction_set_verified_at": reaction_set.get("verified_at"),
        "reaction_count": reaction_set.get("reaction_count", 0),
        "export_formats": list(exports),
        "export_audit_entry_counts": {
            fmt: int(export_payload.get("audit_entry_count") or 0)
            for fmt, export_payload in exports.items()
        },
        "counts": counts,
    }


def write_output_file(path: Path, text: str) -> str | None:
    if path.is_symlink():
        return f"output path is not a regular file: {path}"
    if path.exists() and not path.is_file():
        return f"output path is not a regular file: {path}"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{text}\n", encoding="utf-8")
    except OSError as exc:
        return f"failed to write output file {path}: {exc}"
    return None


def prepare_demo_data(target_lang: str = "zh", verified_by: str = "prepare-demo-data") -> dict:
    configure_storage_defaults()

    from app.config import get_settings
    from app.db import dict_from_row, get_conn, init_db
    from app.routers.system import demo_data_status
    from app.fixture_loader import load_fixture_documents, load_fixture_papers
    from app.services.chemistry import export_reaction_set, extract_reactions
    from app.services.documents import parse_document
    from app.services.rag import index_document
    from app.services.translation import translate_document

    get_settings.cache_clear()
    init_db()
    fixtures = {
        "papers": load_fixture_papers(),
        "documents": load_fixture_documents(),
    }

    with get_conn() as conn:
        document_id = fixture_document_id(conn)

    document = asyncio.run(parse_document(document_id))
    if document.get("parse_status") != "parsed":
        raise RuntimeError(f"demo document parse failed: {document.get('parse_error')}")

    index_result = index_document(document_id)
    if index_result.get("status") != "indexed":
        raise RuntimeError(f"demo document index failed: {index_result.get('error')}")

    translation = translate_document(document_id, target_lang)
    if translation.get("status") != "done":
        raise RuntimeError(f"demo document translation failed: {translation.get('error')}")

    reaction_set = extract_reactions(document_id)
    reactions = reaction_set.get("reactions") or []
    if not reactions:
        raise RuntimeError("demo chemistry extraction produced no reactions")
    verified_reaction_set = verify_all_reactions(reaction_set, verified_by)
    if verified_reaction_set.get("status") != "verified":
        raise RuntimeError("demo reaction set verification did not reach verified status")

    exports = {
        fmt: export_reaction_set(int(verified_reaction_set["id"]), fmt)
        for fmt in ["json", "txt", "bolsig"]
    }

    with get_conn() as conn:
        document_row = conn.execute("SELECT * FROM documents WHERE id=?", (document_id,)).fetchone()
        counts = resource_counts(conn)
    document_payload = dict_from_row(document_row)
    reaction_set_payload = {
        "id": verified_reaction_set.get("id"),
        "status": verified_reaction_set.get("status"),
        "verified_by": verified_reaction_set.get("verified_by"),
        "verified_at": verified_reaction_set.get("verified_at"),
        "reaction_count": len(verified_reaction_set.get("reactions") or []),
    }
    demo_data = demo_data_status(counts)

    return {
        "fixtures": fixtures,
        "document": document_payload,
        "index": index_result,
        "translation": translation,
        "reaction_set": reaction_set_payload,
        "exports": exports,
        "counts": counts,
        "demo_data": demo_data,
        "summary": demo_summary(document_payload, translation, reaction_set_payload, exports, counts, demo_data),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare local walking skeleton demo data.")
    parser.add_argument("--target-lang", default="zh")
    parser.add_argument("--verified-by", default="prepare-demo-data")
    parser.add_argument("--compact", action="store_true", help="Print JSON on one line")
    parser.add_argument("--summary-only", action="store_true", help="Print only the release/demo summary object")
    parser.add_argument("--output", type=Path, help="Write the JSON payload to this path instead of stdout")
    args = parser.parse_args()

    payload = prepare_demo_data(args.target_lang, args.verified_by)
    output = payload["summary"] if args.summary_only else payload
    text = json.dumps(output, ensure_ascii=False, indent=None if args.compact else 2)
    if args.output is None:
        print(text)
    else:
        output_error = write_output_file(args.output, text)
        if output_error:
            print(f"prepare_demo_data failed: {output_error}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
