import { notFound } from "next/navigation";
import Link from "next/link";
import { getPaper, getDownloadedPdfPath } from "@/lib/library/papers";
import { listPaperSegments } from "@/lib/library/segments";

export const dynamic = "force-dynamic";

export default function ReaderPage({
  params,
}: {
  params: { paperId: string };
}) {
  const paper = (() => {
    try { return getPaper(params.paperId); } catch { return null; }
  })();
  if (!paper) {
    notFound();
  }

  let segments: ReturnType<typeof listPaperSegments> = [];
  try { segments = listPaperSegments(params.paperId); } catch { segments = []; }

  // `getDownloadedPdfPath` returns null when status is not "succeeded",
  // so we only show the local-PDF link for papers that actually
  // downloaded. download_failed papers surface their reason in a
  // warn-box so the user can see what went wrong.
  const localPdfPath = (() => {
    try { return getDownloadedPdfPath(params.paperId); } catch { return null; }
  })();

  return (
    <div>
      <p className="muted">
        <Link href="/library">← back to Library</Link>
      </p>
      <h1>{paper.title}</h1>
      <p className="muted">
        {paper.authors.join(", ")} · paper id: <span className="code">{paper.paperId}</span>
      </p>

      <section className="card">
        <h2>Download state</h2>
        {localPdfPath ? (
          <p>
            <span className="badge good">downloaded</span>{" "}
            <span className="code">{localPdfPath}</span>
          </p>
        ) : paper.downloadStatus === "download_failed" ? (
          <div className="warn-box">
            <span className="badge bad">download failed</span>{" "}
            reason: <span className="code">{paper.downloadError ?? "unknown"}</span>
          </div>
        ) : (
          <p className="muted">
            <span className="badge warn">not downloaded</span>{" "}
            Use the Sources page or <span className="code">pnpm intake:download</span> to
            fetch the open PDF.
          </p>
        )}
      </section>

      <h2>Bilingual Reader</h2>
      <p className="muted">
        Paragraph-level alignment. English on the left, Chinese on the right.
        Segment id and order are identical across both columns. Rows where
        the right side says <span className="code">(中文待翻译)</span> come
        from the parsed PDF and have not been translated yet.
      </p>

      <div className="bilingual">
        <div className="col">
          <h3>English</h3>
          {segments.map((seg) => (
            <div className="seg" key={`en-${seg.segmentId}`}>
              <div>
                <div className="seg-id">{seg.segmentId}</div>
                <div className="muted">ord {seg.order}{seg.page ? ` · p.${seg.page}` : ""}</div>
              </div>
              <div className="seg-en">{seg.english}</div>
            </div>
          ))}
        </div>
        <div className="col">
          <h3>中文</h3>
          {segments.map((seg) => (
            <div className="seg" key={`zh-${seg.segmentId}`}>
              <div>
                <div className="seg-id">{seg.segmentId}</div>
                <div className="muted">序号 {seg.order}{seg.page ? ` · p.${seg.page}` : ""}</div>
              </div>
              <div className="seg-zh">
                {seg.chinese && seg.chinese.trim() !== ""
                  ? seg.chinese
                  : <span className="muted">(中文待翻译)</span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
