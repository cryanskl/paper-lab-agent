import json
import re
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


def source_excerpt(text: str, start: int, end: int, window: int = 80) -> str:
    left = max(0, start - window)
    right = min(len(text), end + window)
    return " ".join(text[left:right].split())


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


def detect_cross_section_url(text: str) -> Optional[str]:
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,")
        if "lxcat" in url.lower():
            return url
    return None


def mark_chemistry_queued(document_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET chemistry_status='extracting', chemistry_error=NULL WHERE id=?",
            (document_id,),
        )


def extract_reactions(document_id: int) -> dict:
    with get_conn() as conn:
        conn.execute(
            "UPDATE documents SET chemistry_status='extracting', chemistry_error=NULL WHERE id=?",
            (document_id,),
        )
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            conn.execute(
                "UPDATE documents SET chemistry_status='failed', chemistry_error=? WHERE id=?",
                ("document has no parsed sections", document_id),
            )
            return {"document_id": document_id, "status": "failed", "error": "document has no parsed sections"}
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
            cross_section_url = detect_cross_section_url(text)
            for match in REACTION_RE.finditer(text):
                reaction = " ".join(match.group(1).split())
                normalized_reaction, reactants, products = normalize_reaction(reaction)
                conn.execute(
                    """
                    INSERT INTO reactions (
                        reaction_set_id, reaction, reaction_type, reactants, products,
                        rate_type, rate_value, threshold_ev, reference, cross_section_url,
                        source_section_id, source_excerpt, confidence, verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        reaction_set_id,
                        normalized_reaction,
                        "unknown",
                        json.dumps(reactants, ensure_ascii=False),
                        json.dumps(products, ensure_ascii=False),
                        "unknown",
                        None,
                        None,
                        section["title"],
                        cross_section_url,
                        section["id"],
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
            item["verified_at"] = item.get("created_at")
            reaction["audit_log"].append(item)
    return reaction_set


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
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reactions WHERE id=?", (reaction_id,)).fetchone()
        if not row:
            raise ValueError("reaction not found")
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
        assignments = ", ".join(f"{key}=?" for key in updates)
        conn.execute(
            f"UPDATE reactions SET {assignments} WHERE id=?",
            tuple(updates.values()) + (reaction_id,),
        )
        audit_changes = dict(optional_updates)
        audit_changes["verified"] = verified
        audit_changes = {
            key: value for key, value in audit_changes.items() if value is not None or key in clear_fields
        }
        conn.execute(
            """
            INSERT INTO reaction_audits (reaction_id, action, changes, verified_by)
            VALUES (?, ?, ?, ?)
            """,
            (reaction_id, "verify" if verified else "unverify", json.dumps(audit_changes, ensure_ascii=False), verified_by),
        )
        reaction_set_id = row["reaction_set_id"]
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
            if reaction.get("source_excerpt"):
                lines.append(f"SOURCE_EXCERPT: {reaction['source_excerpt']}")
            lines.append("END")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        mime_type = "text/plain"
    else:
        lines = [f"# {detail.get('name') or 'Reaction set'}"]
        for reaction in detail["reactions"]:
            lines.append(reaction["reaction"])
            if reaction.get("rate_value"):
                lines.append(f"rate: {reaction['rate_value']}")
            if reaction.get("source_section_title"):
                lines.append(f"source_section_title: {reaction['source_section_title']}")
            if reaction.get("source_section_type"):
                lines.append(f"source_section_type: {reaction['source_section_type']}")
            if reaction.get("source_section_seq") is not None:
                lines.append(f"source_section_seq: {reaction['source_section_seq']}")
        out_path.write_text("\n".join(lines), encoding="utf-8")
        mime_type = "text/plain"
    return {"reaction_set_id": reaction_set_id, "format": fmt, "output_path": str(out_path), "mime_type": mime_type}
