import Link from "next/link";
import { listPapers } from "@/lib/library/papers";
import { listIntakeRuns } from "@/lib/intake/import-fixture";
import { getAllSegments } from "@/lib/library/segments";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  let papers: ReturnType<typeof listPapers> = [];
  let runs: ReturnType<typeof listIntakeRuns> = [];
  let segmentCount = 0;
  let loadError: string | null = null;

  try {
    papers = listPapers();
    runs = listIntakeRuns();
    segmentCount = getAllSegments().length;
  } catch (err) {
    loadError = err instanceof Error ? err.message : String(err);
  }

  return (
    <div>
      <h1>paper-lab-agent</h1>
      <p className="muted">
        V1 local-first research assistant. Default mode uses a deterministic
        fake model adapter and fixture-backed data. Run{" "}
        <span className="code">pnpm seed</span> first to load fixtures.
      </p>

      {loadError ? (
        <div className="warn-box">
          Database not initialized yet. Run <span className="code">pnpm seed</span>{" "}
          to load fixtures. <span className="muted">({loadError})</span>
        </div>
      ) : (
        <>
          <section className="card">
            <h2>Library overview</h2>
            <p>
              <strong>{papers.length}</strong> paper(s) ingested ·{" "}
              <strong>{segmentCount}</strong> segment(s) stored ·{" "}
              <strong>{runs.length}</strong> intake run(s) recorded.
            </p>
            <p>
              <Link href="/library">Open Paper Library →</Link>
            </p>
          </section>

          <section className="card">
            <h2>Quick links</h2>
            <ul className="spec-list">
              <li>
                <Link href="/library">Paper Library</Link> — list ingested papers.
              </li>
              <li>
                <Link href="/ask">Ask Papers</Link> — RAG Q&amp;A across all
                ingested papers.
              </li>
              <li>
                <Link href="/simulation">Simulation</Link> — generate a toy
                simulation spec from paper method evidence.
              </li>
            </ul>
          </section>
        </>
      )}
    </div>
  );
}
