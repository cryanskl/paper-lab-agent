import json
import re
from typing import Optional

from app.config import get_settings
from app.db import dict_from_row, get_conn
from app.utils import now_iso


REACTION_RE = re.compile(r"([A-Za-z0-9+()\-\s]+(?:->|=>)[A-Za-z0-9+()\-\s]+)")


def split_species(side: str) -> list[str]:
    return [part.strip() for part in side.split("+") if part.strip()]


def extract_reactions(document_id: int) -> dict:
    with get_conn() as conn:
        sections = conn.execute("SELECT * FROM sections WHERE document_id=? ORDER BY seq", (document_id,)).fetchall()
        if not sections:
            raise ValueError("document has no parsed sections")
        cursor = conn.execute(
            """
            INSERT INTO reaction_sets (document_id, name, gas_mixture, lxcat_db, source_note, status)
            VALUES (?, ?, ?, ?, ?, 'pending')
            """,
            (document_id, "Extracted reaction set", None, None, "Extracted from parsed sections"),
        )
        reaction_set_id = cursor.lastrowid
        found = 0
        for section in sections:
            text = section["content"] or ""
            for match in REACTION_RE.finditer(text):
                reaction = " ".join(match.group(1).split())
                arrow = "=>" if "=>" in reaction else "->"
                left, right = reaction.split(arrow, 1)
                conn.execute(
                    """
                    INSERT INTO reactions (
                        reaction_set_id, reaction, reaction_type, reactants, products,
                        rate_type, rate_value, threshold_ev, reference, cross_section_url,
                        confidence, verified
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                    """,
                    (
                        reaction_set_id,
                        reaction.replace("=>", "->"),
                        "unknown",
                        json.dumps(split_species(left), ensure_ascii=False),
                        json.dumps(split_species(right), ensure_ascii=False),
                        "unknown",
                        None,
                        None,
                        section["title"],
                        None,
                        0.5,
                    ),
                )
                found += 1
        if found == 0:
            conn.execute("UPDATE reaction_sets SET status='rejected', source_note=? WHERE id=?", ("No reaction expressions found", reaction_set_id))
        row = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        return reaction_set_detail(dict_from_row(row), conn)


def reaction_set_detail(reaction_set: dict, conn=None) -> dict:
    if conn is None:
        with get_conn() as owned_conn:
            return reaction_set_detail(reaction_set, owned_conn)
    rows = conn.execute("SELECT * FROM reactions WHERE reaction_set_id=? ORDER BY id", (reaction_set["id"],)).fetchall()
    reaction_set["reactions"] = [dict_from_row(row) for row in rows]
    for reaction in reaction_set["reactions"]:
        reaction["reactants"] = json.loads(reaction["reactants"] or "[]")
        reaction["products"] = json.loads(reaction["products"] or "[]")
        reaction["verified"] = bool(reaction["verified"])
    return reaction_set


def verify_reaction(reaction_id: int, verified: bool, rate_value: Optional[str], verified_by: Optional[str]) -> dict:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM reactions WHERE id=?", (reaction_id,)).fetchone()
        if not row:
            raise ValueError("reaction not found")
        if rate_value is not None:
            conn.execute(
                "UPDATE reactions SET verified=?, rate_value=? WHERE id=?",
                (1 if verified else 0, rate_value, reaction_id),
            )
        else:
            conn.execute("UPDATE reactions SET verified=? WHERE id=?", (1 if verified else 0, reaction_id))
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
        rs = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        return reaction_set_detail(dict_from_row(rs), conn)


def export_reaction_set(reaction_set_id: int, fmt: str) -> dict:
    settings = get_settings()
    with get_conn() as conn:
        rs = conn.execute("SELECT * FROM reaction_sets WHERE id=?", (reaction_set_id,)).fetchone()
        if not rs:
            raise ValueError("reaction set not found")
        remaining = conn.execute(
            "SELECT COUNT(*) AS n FROM reactions WHERE reaction_set_id=? AND verified=0",
            (reaction_set_id,),
        ).fetchone()["n"]
        if remaining:
            raise PermissionError("reaction set has unverified reactions")
        detail = reaction_set_detail(dict_from_row(rs), conn)
    suffix = "json" if fmt == "json" else "txt"
    out_path = settings.export_dir / f"reaction-set-{reaction_set_id}.{suffix}"
    if fmt == "json":
        out_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        lines = [f"# {detail.get('name') or 'Reaction set'}"]
        for reaction in detail["reactions"]:
            lines.append(reaction["reaction"])
            if reaction.get("rate_value"):
                lines.append(f"rate: {reaction['rate_value']}")
        out_path.write_text("\n".join(lines), encoding="utf-8")
    return {"reaction_set_id": reaction_set_id, "format": fmt, "output_path": str(out_path)}
