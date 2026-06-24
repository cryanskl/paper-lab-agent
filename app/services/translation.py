import re
from typing import Optional, Protocol

import httpx

from app.config import Settings
from app.config import get_settings
from app.db import dict_from_row, get_conn


FORMULA_RE = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.DOTALL)
PRESERVE_SECTION_TYPES = {"table", "reference"}
MAX_TARGET_LANG_SLUG_LENGTH = 80


class Translator(Protocol):
    def translate(self, text: str, target_lang: str) -> str:
        ...


class LocalEchoTranslator:
    def translate(self, text: str, target_lang: str) -> str:
        return text


class OpenAICompatibleTranslator:
    def __init__(self, api_key: str, base_url: str, model: str, transport: Optional[httpx.BaseTransport] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    def translate(self, text: str, target_lang: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Translate the user text faithfully. Preserve placeholders like <EQ_000> exactly. "
                        "Do not add explanations."
                    ),
                },
                {"role": "user", "content": f"Target language: {target_lang}\n\n{text}"},
            ],
            "temperature": 0,
        }
        with httpx.Client(transport=self.transport, timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def get_translator(settings: Settings) -> Translator:
    if settings.llm_api_key:
        return OpenAICompatibleTranslator(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
    return LocalEchoTranslator()


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


def translate_text_preserving_formulas(text: str, translator: Translator, target_lang: str) -> str:
    masked, formulas = mask_formulas(text)
    translated = translator.translate(masked, target_lang)
    return unmask_formulas(translated, formulas)


def translate_section_text(section: dict, translator: Translator, target_lang: str) -> str:
    text = section["content"] or ""
    if (section.get("section_type") or "").strip().lower() in PRESERVE_SECTION_TYPES:
        return text
    return translate_text_preserving_formulas(text, translator, target_lang)


def has_translatable_text(section: dict) -> bool:
    section_type = (section.get("section_type") or "").strip().lower()
    return section_type not in PRESERVE_SECTION_TYPES and bool((section.get("content") or "").strip())


def safe_target_lang_slug(target_lang: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", (target_lang or "").strip())
    slug = slug.strip(".-")
    return (slug or "target")[:MAX_TARGET_LANG_SLUG_LENGTH]


def create_translation_job(document_id: int, target_lang: str) -> dict:
    with get_conn() as conn:
        cursor = conn.execute(
            """
            INSERT INTO translations (document_id, source_lang, target_lang, status)
            VALUES (?, 'en', ?, 'pending')
            """,
            (document_id, target_lang),
        )
        translation_id = cursor.lastrowid
        row = conn.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
        return dict_from_row(row)


def translate_document(document_id: int, target_lang: str, translation_id: Optional[int] = None) -> dict:
    settings = get_settings()
    if translation_id is None:
        translation_id = create_translation_job(document_id, target_lang)["id"]
    with get_conn() as conn:
        sections = conn.execute(
            "SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)
        ).fetchall()

    try:
        if not sections:
            raise ValueError("document has no parsed sections")
        if not any(has_translatable_text(dict_from_row(row)) for row in sections):
            raise ValueError("document has no translatable section text")
        translator = get_translator(settings)
        note = (
            "> LLM_API_KEY is not configured; target text preserves source text honestly."
            if not settings.llm_api_key
            else f"> Translated with configured model `{settings.llm_model}`."
        )
        blocks = ["# Bilingual Translation", "", note]
        for row in sections:
            section = dict_from_row(row)
            target_text = translate_section_text(section, translator, target_lang)
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
        out_path = settings.translation_dir / f"document-{document_id}-{safe_target_lang_slug(target_lang)}.md"
        out_path.write_text("\n".join(blocks), encoding="utf-8")
        with get_conn() as conn:
            conn.execute(
                "UPDATE translations SET status='done', output_path=?, error=NULL WHERE id=?",
                (str(out_path), translation_id),
            )
            row = conn.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
            return dict_from_row(row)
    except Exception as exc:
        with get_conn() as conn:
            conn.execute(
                "UPDATE translations SET status='failed', output_path=NULL, error=? WHERE id=?",
                (str(exc), translation_id),
            )
            row = conn.execute("SELECT * FROM translations WHERE id=?", (translation_id,)).fetchone()
            return dict_from_row(row)
