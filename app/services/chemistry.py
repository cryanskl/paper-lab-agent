import json
import re
from collections import Counter
from typing import Optional

from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.utils import now_iso


REACTION_SPECIES_CHARS = r"A-Za-z0-9+*()\-\s\u00b0-\u00b3\u00b7\u00b9\u0370-\u03ff\u1d00-\u1d7f\u2070-\u209f\u2212"
REACTION_ARROWS = ("<->", "=>", "->", "→", "⇌", "↔")
REACTION_RE = re.compile(rf"([{REACTION_SPECIES_CHARS}]+(?:{'|'.join(map(re.escape, REACTION_ARROWS))})[{REACTION_SPECIES_CHARS}]+)")
SPECIES_SEPARATOR_RE = re.compile(r"\s*\+\s*(?=[A-Za-z0-9(\u0370-\u03ff\u2070-\u209f\u2212])")
URL_RE = re.compile(r"https?://[^\s),;]+")
LXCAT_DB_RE = re.compile(r"LXCat\s+([A-Za-z0-9_.-]+)", re.IGNORECASE)
GAS_MIXTURE_RE = re.compile(r"\b([A-Z][a-z]?\d?(?:/[A-Z][a-z]?\d?)+)\b")
THRESHOLD_EV_RE = re.compile(
    r"\bthreshold(?:\s+energy)?\s*(?:is|=|:)?\s*([0-9]+(?:\.[0-9]+)?)\s*eV\b",
    re.IGNORECASE,
)
RATE_VALUE_RE = re.compile(
    r"\b(?:rate\s+(?:coefficient|constant)\s*(?:is|=|:)?|k\s*(?:=|:))\s*"
    r"([0-9]+(?:\.[0-9]+)?(?:[eE][+-]?\d+)?"
    r"(?:\s*(?:cm\^?3/s|m\^?3/s|s\^-?1|s-1|1/s))?)\b",
    re.IGNORECASE,
)


def split_species(side: str) -> list[str]:
    return [part.strip() for part in SPECIES_SEPARATOR_RE.split(side) if part.strip()]


def normalize_species(value: str, position: str) -> str:
    tokens = value.strip(" .,:;").split()
    if not tokens:
        return ""
    if position == "leading":
        return tokens[-1].strip(" .,:;")
    return tokens[0].strip(" .,:;")


def normalize_reaction(reaction: str) -> tuple[str, list[str], list[str]]:
    arrow = next(candidate for candidate in REACTION_ARROWS if candidate in reaction)
    left, right = reaction.split(arrow, 1)
    reactants = split_species(left)
    products = split_species(right)
    if reactants:
        reactants[0] = normalize_species(reactants[0], "leading")
    products = [normalize_species(product, "trailing") for product in products]
    reactants = [reactant for reactant in reactants if reactant]
    products = [product for product in products if product]
    normalized = f"{' + '.join(reactants)} -> {' + '.join(products)}"
    return normalized, reactants, products


def infer_reaction_type(reactants: list[str], products: list[str]) -> str:
    reactant_electrons = sum(1 for species in reactants if species == "e")
    product_electrons = sum(1 for species in products if species == "e")
    consumes_positive_ion = any(species.endswith("+") for species in reactants)
    produces_positive_ion = any(species.endswith("+") for species in products)
    produces_negative_ion = any(species.endswith("-") or species.endswith("⁻") for species in products)
    produces_excited_species = any(species.endswith("*") for species in products)
    if reactant_electrons >= 1 and product_electrons > reactant_electrons and produces_positive_ion:
        return "ionization"
    if reactant_electrons >= 1 and produces_negative_ion:
        return "attachment"
    if reactant_electrons >= 1 and produces_excited_species:
        return "excitation"
    if reactant_electrons >= 1 and consumes_positive_ion and product_electrons == 0 and not produces_positive_ion:
        return "recombination"
    if reactant_electrons >= 1 and Counter(reactants) == Counter(products):
        return "elastic"
    return "unknown"


def source_excerpt(text: str, start: int, end: int, window: int = 80) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return " ".join(text[left:right].split())


def detect_threshold_ev(text: str, start: int, end: int, window: int = 120) -> Optional[float]:
    left = max(0, start - window)
    right = min(len(text), end + window)
    candidates = []
    for match in THRESHOLD_EV_RE.finditer(text[left:right]):
        absolute_start = left + match.start()
        absolute_end = left + match.end()
        if absolute_start >= end:
            direction_priority = 0
            distance = absolute_start - end
        elif absolute_end <= start:
            direction_priority = 1
            distance = start - absolute_end
        else:
            direction_priority = 2
            distance = 0
        candidates.append((direction_priority, distance, absolute_start, float(match.group(1))))
    if candidates:
        return min(candidates)[3]
    return None


def detect_rate_value(text: str, start: int, end: int, window: int = 120) -> Optional[str]:
    left = max(0, start - window)
    right = min(len(text), end + window)
    candidates = []
    for match in RATE_VALUE_RE.finditer(text[left:right]):
        absolute_start = left + match.start()
        absolute_end = left + match.end()
        if absolute_start >= end:
            direction_priority = 0
            distance = absolute_start - end
        elif absolute_end <= start:
            direction_priority = 1
            distance = start - absolute_end
        else:
            direction_priority = 2
            distance = 0
        candidates.append((direction_priority, distance, absolute_start, " ".join(match.group(1).split())))
    if candidates:
        return min(candidates)[3]
    return None


def source_label(section: dict) -> str:
    section_type = section.get("section_type") or "section"
    seq = section.get("seq")
    title = section.get("title")
    if seq is not None and title:
        return f"{section_type} {seq}: {title}"
    if title:
        return f"{section_type}: {title}"
    if seq is not None:
        return f"{section_type} {seq}"
    return section_type


def detect_lxcat_db(text: str) -> Optional[str]:
    match = LXCAT_DB_RE.search(text)
    if not match:
        return None
    return match.group(1).strip(" .,:;")


def detect_gas_mixture(text: str) -> Optional[str]:
    match = GAS_MIXTURE_RE.search(text)
    if not match:
        return None
    return match.group(1)


def mask_urls_for_reaction_matching(text: str) -> str:
    def replace(match: re.Match) -> str:
        raw_url = match.group(0)
        url = raw_url.rstrip(".,")
        suffix = raw_url[len(url) :]
        return (" " * len(url)) + suffix

    return URL_RE.sub(replace, text)


def detect_cross_section_url(text: str, start: Optional[int] = None, end: Optional[int] = None) -> Optional[str]:
    candidates = []
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,")
        if "lxcat" in url.lower():
            if start is None or end is None:
                return url
            if match.end() <= start:
                distance = start - match.end()
            elif match.start() >= end:
                distance = match.start() - end
            else:
                distance = 0
            candidates.append((distance, match.start(), url))
    if candidates:
        return min(candidates)[2]
    return None


def mark_chemistry_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
        conn.execute(
            "UPDATE documents SET chemistry_status='extracting', chemistry_error=NULL WHERE id=?",
            (document_id,),
        )


def fail_chemistry_extraction(document_id: int, error: str) -> dict:
    with get_conn() as conn:
        conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
        conn.execute(
            "UPDATE documents SET chemistry_status='failed', chemistry_error=? WHERE id=?",
            (error, document_id),
        )
    return {"document_id": document_id, "status": "failed", "error": error}


def extract_reactions(document_id: int) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET chemistry_status='extracting', chemistry_error=NULL WHERE id=?",
            (document_id,),
        )
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
            conn.execute(
                "UPDATE documents SET chemistry_status='failed', chemistry_error=? WHERE id=?",
                ("document has no parsed sections", document_id),
            )
            return {"document_id": document_id, "status": "failed", "error": "document has no parsed sections"}
        if not any((section["content"] or "").strip() for section in sections):
            conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
            conn.execute(
                "UPDATE documents SET chemistry_status='failed', chemistry_error=? WHERE id=?",
                ("document has no extractable section text", document_id),
            )
            return {"document_id": document_id, "status": "failed", "error": "document has no extractable section text"}

    try:
        with get_conn() as conn:
            conn.execute("DELETE FROM reaction_sets WHERE document_id=?", (document_id,))
            cursor = conn.execute(
                """
                INSERT INTO reaction_sets (document_id, name, gas_mixture, lxcat_db, source_note, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (document_id, "Extracted reaction set", None, None, "Extracted from parsed sections"),
            )
            reaction_set_id = cursor.lastrowid
            found = 0
            detected_gas_mixture = None
            detected_lxcat_db = None
            for section in sections:
                text = section["content"] or ""
                detected_gas_mixture = detected_gas_mixture or detect_gas_mixture(text)
                detected_lxcat_db = detected_lxcat_db or detect_lxcat_db(text)
                section_cross_section_url = detect_cross_section_url(text)
                reaction_search_text = mask_urls_for_reaction_matching(text)
                for match in REACTION_RE.finditer(reaction_search_text):
                    reaction = " ".join(match.group(1).split())
                    normalized_reaction, reactants, products = normalize_reaction(reaction)
                    cross_section_url = (
                        detect_cross_section_url(text, match.start(), match.end()) or section_cross_section_url
                    )
                    threshold_ev = detect_threshold_ev(text, match.start(), match.end())
                    rate_value = detect_rate_value(text, match.start(), match.end())
                    if rate_value:
                        rate_type = "constant"
                    elif cross_section_url:
                        rate_type = "cross_section"
                    else:
                        rate_type = "unknown"
                    conn.execute(
                        """
                        INSERT INTO reactions (
                            reaction_set_id, reaction, reaction_type, reactants, products,
                            rate_type, rate_value, threshold_ev, reference, cross_section_url,
                            source_section_id, source_label, source_excerpt, confidence, verified
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                        """,
                        (
                            reaction_set_id,
                            normalized_reaction,
                            infer_reaction_type(reactants, products),
                            json.dumps(reactants, ensure_ascii=False),
                            json.dumps(products, ensure_ascii=False),
                            rate_type,
                            rate_value,
                            threshold_ev,
                            section["title"],
                            cross_section_url,
                            section["id"],
                            source_label(dict_from_row(section)),
                            source_excerpt(text, match.start(), match.end()),
                            0.5,
                        ),
                    )
                    found += 1
            if detected_gas_mixture:
                conn.execute("UPDATE reaction_sets SET gas_mixture=? WHERE id=?", (detected_gas_mixture, reaction_set_id))
            if detected_lxcat_db:
                conn.execute("UPDATE reaction_sets SET lxcat_db=? WHERE id=?", (detected_lxcat_db, reaction_set_id))
            if found == 0:
                conn.execute("UPDATE reaction_sets SET status='rejected', source_note=? WHERE id=?", ("No reaction expressions found", reaction_set_id))
                conn.execute(
                    "UPDATE documents SET chemistry_status='rejected', chemistry_error=? WHERE id=?",
                    ("No reaction expressions found", document_id),
                )
            else:
                conn.execute(
                    "UPDATE documents SET chemistry_status='extracted', chemistry_error=NULL WHERE id=?",
                    (document_id,),
                )
            row = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
            return reaction_set_detail(dict_from_row(row), conn)
    except Exception as exc:
        return fail_chemistry_extraction(document_id, str(exc))


def reaction_set_detail(reaction_set: dict, conn=None) -> dict:
    if conn is None:
        with get_conn() as owned_conn:
            return reaction_set_detail(reaction_set, owned_conn)
    rows = conn.execute(
        """
        SELECT
            reactions.*,
            sections.title AS source_section_title,
            sections.section_type AS source_section_type,
            sections.seq AS source_section_seq
        FROM reactions
        LEFT JOIN sections ON sections.id = reactions.source_section_id
        WHERE reactions.reaction_set_id=?
        ORDER BY reactions.id
        """,
        (reaction_set["id"],),
    ).fetchall()
    reaction_set["reactions"] = [dict_from_row(row) for row in rows]
    for reaction in reaction_set["reactions"]:
        reaction["reactants"] = json.loads(reaction["reactants"] or "[]")
        reaction["products"] = json.loads(reaction["products"] or "[]")
        reaction["verified"] = bool(reaction["verified"])
        audits = conn.execute(
            "SELECT * FROM reaction_audits WHERE reaction_id=? ORDER BY id DESC",
            (reaction["id"],),
        ).fetchall()
        reaction["audit_log"] = []
        for audit in audits:
            item = dict_from_row(audit)
            item["changes"] = json.loads(item.get("changes") or "{}")
            item["field_changes"] = item["changes"].pop("_field_changes", {})
            item["verified_at"] = item.get("created_at")
            reaction["audit_log"].append(item)
    reaction_set["reaction_count"] = len(reaction_set["reactions"])
    reaction_set["verified_count"] = sum(1 for reaction in reaction_set["reactions"] if reaction.get("verified"))
    reaction_set["unverified_count"] = reaction_set["reaction_count"] - reaction_set["verified_count"]
    reaction_set["export_ready"] = reaction_set["reaction_count"] > 0 and reaction_set["unverified_count"] == 0
    return reaction_set


def reconcile_reaction_set_review_state(conn, reaction_set_id: int, verified_by: Optional[str]) -> None:
    remaining = conn.execute(
        "SELECT COUNT(*) AS n FROM reactions WHERE reaction_set_id=? AND verified=0",
        (reaction_set_id,),
    ).fetchone()["n"]
    if remaining == 0:
        conn.execute(
            "UPDATE reaction_sets SET status='verified', verified_by=?, verified_at=? WHERE id=?",
            (verified_by, now_iso(), reaction_set_id),
        )
    else:
        conn.execute(
            "UPDATE reaction_sets SET status='pending', verified_by=NULL, verified_at=NULL WHERE id=?",
            (reaction_set_id,),
        )


def verify_reaction(
    reaction_id: int,
    verified: bool,
    rate_value: Optional[str],
    verified_by: Optional[str],
    reaction_type: Optional[str] = None,
    rate_type: Optional[str] = None,
    threshold_ev: Optional[float] = None,
    cross_section_url: Optional[str] = None,
    clear_fields: Optional[set[str]] = None,
) -> dict:
    def audit_value(field: str, value):
        return bool(value) if field == "verified" else value

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reactions WHERE id=?", (reaction_id,)).fetchone()
        if not row:
            raise ValueError("reaction not found")
        before = dict_from_row(row)
        updates = {"verified": 1 if verified else 0}
        clear_fields = clear_fields or set()
        optional_updates = {
            "reaction_type": reaction_type,
            "rate_type": rate_type,
            "rate_value": rate_value,
            "threshold_ev": threshold_ev,
            "cross_section_url": cross_section_url,
        }
        for key, value in optional_updates.items():
            if value is not None:
                updates[key] = value
            elif key in clear_fields:
                updates[key] = None
        changed_updates = {
            key: value
            for key, value in updates.items()
            if audit_value(key, before[key]) != audit_value(key, value)
        }
        reaction_set_id = row["reaction_set_id"]
        if not changed_updates:
            conn.execute(
                """
                INSERT INTO reaction_audits (reaction_id, action, changes, verified_by)
                VALUES (?, ?, ?, ?)
                """,
                (
                    reaction_id,
                    "verify" if verified else "unverify",
                    json.dumps({"_field_changes": {}}, ensure_ascii=False),
                    verified_by,
                ),
            )
            reconcile_reaction_set_review_state(conn, reaction_set_id, verified_by)
            rs = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
            return reaction_set_detail(dict_from_row(rs), conn)
        assignments = ", ".join(f"{key}=?" for key in changed_updates)
        conn.execute(
            f"UPDATE reactions SET {assignments} WHERE id=?",
            tuple(changed_updates.values()) + (reaction_id,),
        )
        audit_changes = {key: value for key, value in changed_updates.items()}
        audit_changes["_field_changes"] = {
            key: {"before": audit_value(key, before[key]), "after": audit_value(key, value)}
            for key, value in audit_changes.items()
        }
        conn.execute(
            """
            INSERT INTO reaction_audits (reaction_id, action, changes, verified_by)
            VALUES (?, ?, ?, ?)
            """,
            (reaction_id, "verify" if verified else "unverify", json.dumps(audit_changes, ensure_ascii=False), verified_by),
        )
        reconcile_reaction_set_review_state(conn, reaction_set_id, verified_by)
        rs = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        return reaction_set_detail(dict_from_row(rs), conn)


def export_reaction_set(reaction_set_id: int, fmt: str) -> dict:
    fmt = (fmt or "").strip().lower()
    if fmt not in {"json", "txt", "bolsig"}:
        raise ValueError(f"unsupported export format: {fmt}")
    settings = get_settings()
    with get_conn() as conn:
        rs = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        if not rs:
            raise ValueError("reaction set not found")
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM reactions WHERE reaction_set_id=? AND verified=0",
            (reaction_set_id,),
        ).fetchone()["n"]
        total = conn.execute(
            "SELECT COUNT(*) AS n FROM reactions WHERE reaction_set_id=?",
            (reaction_set_id,),
        ).fetchone()["n"]
        if total == 0:
            raise PermissionError("reaction set has no reactions to export")
        if remaining:
            raise PermissionError("reaction set has unverified reactions")
        detail = reaction_set_detail(dict_from_row(rs), conn)
    reaction_count = len(detail["reactions"])
    audit_entry_count = sum(len(reaction.get("audit_log") or []) for reaction in detail["reactions"])
    suffix_by_format = {"json": "json", "txt": "txt", "bolsig": "bolsig.txt"}
    out_path = settings.export_dir / f"reaction-set-{reaction_set_id}.{suffix_by_format[fmt]}"
    if fmt == "json":
        out_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        mime_type = "application/json"
    elif fmt == "bolsig":
        lines = [
            "# BOLSIG+ / LXCat compatible reaction summary",
            f"# reaction_set_id: {reaction_set_id}",
            f"# name: {detail.get('name') or 'Reaction set'}",
        ]
        if detail.get("gas_mixture"):
            lines.append(f"# gas_mixture: {detail['gas_mixture']}")
        if detail.get("lxcat_db"):
            lines.append(f"# lxcat_db: {detail['lxcat_db']}")
        if detail.get("verified_by"):
            lines.append(f"# VERIFIED_BY: {detail['verified_by']}")
        if detail.get("verified_at"):
            lines.append(f"# VERIFIED_AT: {detail['verified_at']}")
        for index, reaction in enumerate(detail["reactions"], start=1):
            lines.extend(
                [
                    "",
                    f"PROCESS {index}",
                    f"REACTION: {reaction['reaction']}",
                    f"TYPE: {reaction.get('reaction_type') or 'unknown'}",
                    f"RATE_TYPE: {reaction.get('rate_type') or 'unknown'}",
                ]
            )
            if reaction.get("threshold_ev") is not None:
                lines.append(f"THRESHOLD_EV: {reaction['threshold_ev']}")
            if reaction.get("confidence") is not None:
                lines.append(f"CONFIDENCE: {reaction['confidence']}")
            if reaction.get("rate_value"):
                lines.append(f"RATE_VALUE: {reaction['rate_value']}")
            if reaction.get("cross_section_url"):
                lines.append(f"CROSS_SECTION_URL: {reaction['cross_section_url']}")
            if reaction.get("reference"):
                lines.append(f"REFERENCE: {reaction['reference']}")
            if reaction.get("source_section_id"):
                lines.append(f"SOURCE_SECTION_ID: {reaction['source_section_id']}")
            if reaction.get("source_section_title"):
                lines.append(f"SOURCE_SECTION_TITLE: {reaction['source_section_title']}")
            if reaction.get("source_section_type"):
                lines.append(f"SOURCE_SECTION_TYPE: {reaction['source_section_type']}")
            if reaction.get("source_section_seq") is not None:
                lines.append(f"SOURCE_SECTION_SEQ: {reaction['source_section_seq']}")
            if reaction.get("source_label"):
                lines.append(f"SOURCE_LABEL: {reaction['source_label']}")
            if reaction.get("source_excerpt"):
                lines.append(f"SOURCE_EXCERPT: {reaction['source_excerpt']}")
            lines.append("END")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        mime_type = "text/plain"
    else:
        lines = [f"# {detail.get('name') or 'Reaction set'}"]
        if detail.get("verified_by"):
            lines.append(f"verified_by: {detail['verified_by']}")
        if detail.get("verified_at"):
            lines.append(f"verified_at: {detail['verified_at']}")
        for reaction in detail["reactions"]:
            lines.append(reaction["reaction"])
            if reaction.get("confidence") is not None:
                lines.append(f"confidence: {reaction['confidence']}")
            if reaction.get("rate_value"):
                lines.append(f"rate: {reaction['rate_value']}")
            if reaction.get("source_section_title"):
                lines.append(f"source_section_title: {reaction['source_section_title']}")
            if reaction.get("source_section_type"):
                lines.append(f"source_section_type: {reaction['source_section_type']}")
            if reaction.get("source_section_seq") is not None:
                lines.append(f"source_section_seq: {reaction['source_section_seq']}")
            if reaction.get("source_label"):
                lines.append(f"source_label: {reaction['source_label']}")
            if reaction.get("source_excerpt"):
                lines.append(f"source_excerpt: {reaction['source_excerpt']}")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        mime_type = "text/plain"
    return {
        "reaction_set_id": reaction_set_id,
        "format": fmt,
        "output_path": str(out_path),
        "mime_type": mime_type,
        "reaction_count": reaction_count,
        "audit_entry_count": audit_entry_count,
    }
