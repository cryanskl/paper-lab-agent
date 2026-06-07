import Link from "next/link";
import { listPapers } from "@/lib/library/papers";

export const dynamic = "force-dynamic";

export default function LibraryPage() {
  let papers: ReturnType<typeof listPapers> = [];
  let loadError: string | null = null;
  try {
    papers = listPapers();
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }

  return (
    <div>
      <h1>Paper Library</h1>
      <p className="muted">
        Fixture-backed V1 library. Click a paper to open the bilingual reader.
      </p>

      {loadError ? (
        <div className="warn-box">
          Database not initialized. Run <span className="code">pnpm seed</span>.
        </div>
      ) : papers.length === 0 ? (
        <p className="empty">No papers yet. Run <span className="code">pnpm seed</span> to load fixtures.</p>
      ) : (
        <div className="paper-list">
          {papers.map((paper) => (
            <div className="card" key={paper.paperId}>
              <div className="row">
                <span className="order code">{paper.paperId}</span>
                <div style={{ flex: 1 }}>
                  <div className="title">
                    <Link href={`/library/${paper.paperId}`}>{paper.title}</Link>
                  </div>
                  <div className="meta">
                    {paper.authors.join(", ")} · {paper.publishedAt ?? "unknown date"} · source: {paper.source}
                  </div>
                  <div className="meta">
                    {paper.status === "accepted" ? (
                      <span className="badge good">accepted</span>
                    ) : (
                      <span className="badge bad">rejected</span>
                    )}
                    <span className="badge warn">{paper.downloadStatus}</span>
                  </div>
                  <p style={{ marginTop: 8 }}>{paper.abstract}</p>
                  <p className="muted">
                    Rationale: {paper.relevanceRationale}
                  </p>
                  <p className="muted">
                    <a href={paper.sourceUrl} target="_blank" rel="noreferrer">source link</a>
                    {paper.pdfUrl ? (
                      <>
                        {" · "}
                        <a href={paper.pdfUrl} target="_blank" rel="noreferrer">pdf link</a>
                      </>
                    ) : null}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
