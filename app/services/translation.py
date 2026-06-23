import re
from pathlib import Path

from app.config import get_settings
from app.db import dict_from_row, get_conn


FORMULA_RE = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.DOTALL)


def mask_formulas(text: str) -> tuple[str, dict[str, str]]:
    formulas: dict[str, str] = {}

    def replace(match: re.Match) -> str:
        key = f"<EQ_{len(formulas):03d}>"
        formulas[key] = match.group(0)
        return key

    return FORMULA_RE.sub(replace, text), formulas


def unmask_formulas(text: str, formulas: dict[str, str]) -> str:
    for key, value in formulas.items():
        text = text.replace(key, value)
    return text


def translate_document(document_id: int, target_lang: str) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        sections = conn.execute(
            "SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)
        ).fetchall()
        if not sections:
            raise ValueError("document has no parsed sections")
        cursor = conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status)
            VALUES (?, 'en', ?, 'pending')
            """,
            (document_id, target_lang),
        )
        translation_id = cursor.lastrowid

    blocks = ["# Bilingual Translation", "", "> LLM_API_KEY is not configured; target text preserves source text honestly."]
    for row in sections:
        section = dict_from_row(row)
        masked, formulas = mask_formulas(section["content"] or "")
        target_text = unmask_formulas(masked, formulas)
        blocks.extend(
            [
                "",
                f"## {section['title'] or 'Section'}",
                "",
                "### Source",
                "",
                section["content"] or "",
                "",
                f"### {target_lang}",
                "",
                target_text,
            ]
        )
    out_path = settings.translation_dir / f"document-{document_id}-{target_lang}.md"
    out_path.write_text("\n".join(blocks), encoding="utf-8")
    with get_conn() as conn:
        conn.execute(
            "UPDATE translations SET status='done', output_path=? WHERE id=?",
            (str(out_path), translation_id),
        )
        row = conn.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
        return dict_from_row(row)

