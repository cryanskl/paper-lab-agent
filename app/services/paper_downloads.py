from pathlib import Path
from typing import Any

from app.db import dict_from_row, get_conn
from app.errors import AppError
from app.services.documents import save_document_bytes
from app.services.oa_download import OADownloadError, download_oa_pdf


def local_document_for_paper(conn, paper_id: int):
    return conn.execute(
        """
        SELECT id, paper_id, file_path, original_name, created_at
        FROM documents
        WHERE paper_id=?
        ORDER BY id DESC
        LIMIT 1
        """,
        (paper_id,),
    ).fetchone()


def paper_download_state(conn, paper_id: int, downloadable: bool) -> dict[str, Any]:
    document = local_document_for_paper(conn, paper_id)
    if document is not None:
        return {
            "status": "downloaded",
            "error": None,
            "document_id": document["id"],
            "downloaded_at": document["created_at"],
        }
    row = conn.execute(
        """
        SELECT id, document_id, status, error, updated_at
        FROM paper_downloads
        WHERE paper_id=?
        """,
        (paper_id,),
    ).fetchone()
    if row is not None:
        status = row["status"]
        if status in {"pending", "downloading"}:
            status = "downloading"
        elif status == "downloaded" and row["document_id"] is None:
            status = "failed"
        return {
            "status": status,
            "error": row["error"],
            "document_id": row["document_id"],
            "downloaded_at": row["updated_at"] if status == "downloaded" else None,
        }
    return {
        "status": "available" if downloadable else "unavailable",
        "error": None,
        "document_id": None,
        "downloaded_at": None,
    }


def create_paper_download_job(paper_id: int) -> dict[str, Any]:
    with get_conn() as conn:
        paper = conn.execute(
            "SELECT id, oa_pdf_url FROM papers WHERE id=?",
            (paper_id,),
        ).fetchone()
        if paper is None:
            raise AppError(404, "paper_not_found", "Paper not found")
        existing_document = local_document_for_paper(conn, paper_id)
        if existing_document is not None:
            conn.execute(
                """
                INSERT INTO paper_downloads (
                    paper_id, document_id, status, source_url, file_path, error, updated_at
                )
                VALUES (?, ?, 'downloaded', ?, ?, NULL, datetime('now'))
                ON CONFLICT(paper_id) DO UPDATE SET
                    document_id=excluded.document_id,
                    status='downloaded',
                    source_url=excluded.source_url,
                    file_path=excluded.file_path,
                    error=NULL,
                    updated_at=datetime('now')
                """,
                (
                    paper_id,
                    existing_document["id"],
                    paper["oa_pdf_url"],
                    existing_document["file_path"],
                ),
            )
            row = conn.execute(
                "SELECT * FROM paper_downloads WHERE paper_id=?",
                (paper_id,),
            ).fetchone()
            return dict_from_row(row) | {"already_downloaded": True, "should_start": False}
        source_url = str(paper["oa_pdf_url"] or "").strip()
        if not source_url:
            raise AppError(409, "oa_pdf_unavailable", "Paper has no open-access PDF URL")
        current = conn.execute(
            "SELECT * FROM paper_downloads WHERE paper_id=?",
            (paper_id,),
        ).fetchone()
        if current is not None and current["status"] in {"pending", "downloading"}:
            return dict_from_row(current) | {"already_downloaded": False, "should_start": False}
        conn.execute(
            """
            INSERT INTO paper_downloads (
                paper_id, document_id, status, source_url, file_path, error, updated_at
            )
            VALUES (?, NULL, 'downloading', ?, NULL, NULL, datetime('now'))
            ON CONFLICT(paper_id) DO UPDATE SET
                document_id=NULL,
                status='downloading',
                source_url=excluded.source_url,
                file_path=NULL,
                error=NULL,
                updated_at=datetime('now')
            """,
            (paper_id, source_url),
        )
        row = conn.execute(
            "SELECT * FROM paper_downloads WHERE paper_id=?",
            (paper_id,),
        ).fetchone()
        return dict_from_row(row) | {"already_downloaded": False, "should_start": True}


def mark_download_failed(paper_id: int, message: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE paper_downloads
            SET status='failed', document_id=NULL, file_path=NULL, error=?, updated_at=datetime('now')
            WHERE paper_id=?
            """,
            (message, paper_id),
        )


async def download_paper_to_library(paper_id: int, user_agent: str) -> None:
    with get_conn() as conn:
        paper = conn.execute(
            "SELECT id, title, oa_pdf_url FROM papers WHERE id=?",
            (paper_id,),
        ).fetchone()
    if paper is None:
        mark_download_failed(paper_id, "Paper not found")
        return
    source_url = str(paper["oa_pdf_url"] or "").strip()
    if not source_url:
        mark_download_failed(paper_id, "Paper has no open-access PDF URL")
        return
    try:
        downloaded = await download_oa_pdf(source_url, user_agent=user_agent)
        document, _created = save_document_bytes(
            downloaded.content,
            paper_id,
            f"{paper['title']}.pdf",
        )
        if document.get("paper_id") != paper_id:
            raise OSError(
                f"PDF already belongs to paper {document.get('paper_id')}"
            )
        path = Path(document["file_path"])
        with get_conn() as conn:
            conn.execute(
                """
                UPDATE paper_downloads
                SET document_id=?, status='downloaded', source_url=?, file_path=?,
                    error=NULL, updated_at=datetime('now')
                WHERE paper_id=?
                """,
                (document["id"], downloaded.final_url, str(path), paper_id),
            )
    except OADownloadError as exc:
        mark_download_failed(paper_id, exc.message)
    except Exception as exc:
        mark_download_failed(paper_id, str(exc))
