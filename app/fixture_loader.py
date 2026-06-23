from app.db import get_conn
from app.utils import json_dumps


FIXTURE_PAPERS = [
    {
        "doi": "10.1088/1361-6595/fixture-ar-o2",
        "title": "Global model of an Ar/O2 inductively coupled plasma",
        "abstract": "A fixture paper about low temperature plasma chemistry, reaction kinetics, and plasma simulation.",
        "journal_id": 2,
        "journal_name": "Plasma Sources Science and Technology",
        "published_date": "2026-01-15",
        "published_year": 2026,
        "landing_url": "https://example.test/papers/ar-o2-icp",
        "oa_status": "green",
        "oa_pdf_url": "https://example.test/papers/ar-o2-icp.pdf",
        "source_api": "fixture",
    },
    {
        "doi": "10.1063/fixture-ccp-sheath",
        "title": "Sheath dynamics in capacitively coupled plasma simulations",
        "abstract": "A fixture paper about sheath physics, diagnostics, and low temperature plasma methods.",
        "journal_id": 1,
        "journal_name": "Physics of Plasmas",
        "published_date": "2025-11-02",
        "published_year": 2025,
        "landing_url": "https://example.test/papers/ccp-sheath",
        "oa_status": "unknown",
        "oa_pdf_url": None,
        "source_api": "fixture",
    },
]


def load_fixture_papers() -> dict:
    inserted = 0
    updated = 0
    with get_conn() as conn:
        for paper in FIXTURE_PAPERS:
            existing = conn.execute("SELECT id FROM papers WHERE doi=?", (paper["doi"],)).fetchone()
            params = (
                paper["doi"],
                paper["title"],
                paper["abstract"],
                json_dumps([]),
                paper["journal_id"],
                paper["journal_name"],
                paper["published_date"],
                paper["published_year"],
                paper["landing_url"],
                paper["oa_status"],
                paper["oa_pdf_url"],
                paper["source_api"],
                json_dumps({"fixture": True}),
            )
            if existing:
                conn.execute(
                    """
                    UPDATE papers SET title=?, abstract=?, authors=?, journal_id=?, journal_name=?,
                        published_date=?, published_year=?, landing_url=?, oa_status=?, oa_pdf_url=?,
                        source_api=?, raw_metadata=?, updated_at=datetime('now')
                    WHERE doi=?
                    """,
                    params[1:] + (paper["doi"],),
                )
                updated += 1
            else:
                conn.execute(
                    """
                    INSERT INTO papers (
                        doi, title, abstract, authors, journal_id, journal_name, published_date,
                        published_year, landing_url, oa_status, oa_pdf_url, source_api, raw_metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    params,
                )
                inserted += 1
    return {"inserted": inserted, "updated": updated}

