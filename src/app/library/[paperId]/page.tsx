import { notFound } from "next/navigation";
import Link from "next/link";
import { getPaper } from "@/lib/library/papers";
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

  return (
    <div>
      <p className="muted">
        <Link href="/library">← back to Library</Link>
      </p>
      <h1>{paper.title}</h1>
      <p className="muted">
        {paper.authors.join(", ")} · paper id: <span className="code">{paper.paperId}</span>
      </p>

      <h2>Bilingual Reader</h2>
      <p className="muted">
        Paragraph-level alignment. English on the left, Chinese on the right.
        Segment id and order are identical across both columns.
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
              <div className="seg-zh">{seg.chinese}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
