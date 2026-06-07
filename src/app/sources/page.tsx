// Sources & Profile page.
//
// Five sections:
//   1) Local research profile — view + edit, persisted to data/profile.json.
//   2) Manual intake run control — fixture import and (opt-in) live arXiv.
//   3) Open-PDF download control — opt-in bulk download for accepted papers.
//   4) Local model selection — view provider and (opt-in) health probe.
//   5) Recent intake run history with source / query / counts.

import { loadProfileFromPath, resolveProfilePath } from "@/lib/profile";
import { listIntakeRuns } from "@/lib/intake/import-fixture";
import { isFixtureSource } from "@/lib/intake/run-intake";
import {
  saveProfileAction,
  runFixtureIntakeAction,
  runLiveArxivIntakeAction,
  runDownloadAllAction,
  runModelHealthAction,
} from "./actions";
import {
  currentModelProviderName,
  isOllamaLiveOptedIn,
  describeModelSelection,
} from "@/lib/sources/policy";

export const dynamic = "force-dynamic";

interface SourcesPageProps {
  searchParams: Promise<{ live?: string; download?: string; model?: string }>;
}

function liveOptedIn(): boolean {
  return process.env.PAPER_LAB_LIVE_INTAKE_OPT_IN === "true";
}

function downloadLiveOptedIn(): boolean {
  return process.env.PAPER_LAB_DOWNLOAD_LIVE_OPT_IN === "true";
}

export default async function SourcesPage({ searchParams }: SourcesPageProps) {
  const { live, download, model } = await searchParams;
  const profile = loadProfileFromPath(resolveProfilePath(process.env.PAPER_LAB_PROFILE_PATH));
  const runs = listIntakeRuns().slice(0, 10);
  const liveEnabled = liveOptedIn();
  const downloadLiveEnabled = downloadLiveOptedIn();
  const modelProvider = currentModelProviderName(process.env.PAPER_LAB_MODEL_PROVIDER);
  const ollamaLiveEnabled = isOllamaLiveOptedIn(process.env.PAPER_LAB_LIVE_MODEL_OPT_IN);
  const modelSummary = describeModelSelection(modelProvider, ollamaLiveEnabled);
  const showModelHealthButton = modelProvider === "ollama" && ollamaLiveEnabled;

  return (
    <div>
      <h1>Sources &amp; Profile</h1>
      <p className="muted">
        Configure your local research profile and trigger manual intake runs.
        Live arXiv intake is opt-in; the default is fixture-backed so the
        app never hits the network on its own.
      </p>

      {live === "blocked" ? (
        <div className="warn-box">
          Live arXiv intake was blocked. Set{" "}
          <span className="code">PAPER_LAB_LIVE_INTAKE_OPT_IN=true</span> in
          your local <span className="code">.env</span> and restart the app.
        </div>
      ) : null}
      {live === "ok" ? (
        <div className="card" style={{ borderColor: "#3a7" }}>
          Live arXiv intake finished. The newest <span className="code">arxiv</span> run is
          listed below.
        </div>
      ) : null}
      {download === "done" ? (
        <div className="card" style={{ borderColor: "#3a7" }}>
          Download pass finished. The most recent rows above now reflect
          the new <span className="code">downloadStatus</span>.
        </div>
      ) : null}
      {model === "done" ? (
        <div className="card" style={{ borderColor: "#3a7" }}>
          Local model health probe finished. Check the server logs for
          the result.
        </div>
      ) : null}
      {model === "ok" ? (
        <div className="card">
          The active provider is <span className="code">{modelProvider}</span> —
          no network probe is needed. Configure{" "}
          <span className="code">PAPER_LAB_MODEL_PROVIDER=ollama</span> and{" "}
          <span className="code">PAPER_LAB_LIVE_MODEL_OPT_IN=true</span> to probe
          a local Ollama instance.
        </div>
      ) : null}

      <section className="card">
        <h2>Research profile</h2>
        <p className="muted">
          Saved to <span className="code">data/profile.json</span> (overridable
          via <span className="code">PAPER_LAB_PROFILE_PATH</span>).
        </p>
        <form action={saveProfileAction} className="form">
          <label className="field">
            <span>Keywords (comma or newline separated)</span>
            <textarea
              name="keywords"
              defaultValue={profile.keywords.join(", ")}
              rows={4}
              spellCheck={false}
            />
          </label>
          <label className="field">
            <span>arXiv query</span>
            <input
              type="text"
              name="arxivQuery"
              defaultValue={profile.arxivQuery}
              spellCheck={false}
            />
          </label>
          <div className="row">
            <label className="field" style={{ flex: 1 }}>
              <span>Max candidates per run</span>
              <input
                type="number"
                name="maxCandidates"
                defaultValue={String(profile.maxCandidates)}
                min={1}
                max={50}
              />
            </label>
            <label className="field" style={{ flex: 1 }}>
              <span>Source</span>
              <input
                type="text"
                name="source"
                defaultValue={profile.source}
                spellCheck={false}
              />
            </label>
          </div>
          <label className="field">
            <span>Seed paper ids (comma or newline separated, optional)</span>
            <input
              type="text"
              name="seedPaperIds"
              defaultValue={profile.seedPaperIds.join(", ")}
              spellCheck={false}
            />
          </label>
          <div className="row">
            <button type="submit" className="primary">Save profile</button>
          </div>
        </form>
      </section>

      <section className="card">
        <h2>Run intake</h2>
        <p className="muted">
          Fixture intake always works and never touches the network. Live
          arXiv intake is opt-in via{" "}
          <span className="code">PAPER_LAB_LIVE_INTAKE_OPT_IN</span> in
          your <span className="code">.env</span>.
        </p>
        <div className="row">
          <form action={runFixtureIntakeAction}>
            <button type="submit" className="primary">
              Run fixture intake
            </button>
          </form>
          <form action={runLiveArxivIntakeAction}>
            <button type="submit" disabled={!liveEnabled} title={
              liveEnabled
                ? "Fetch arXiv metadata and persist candidates"
                : "Set PAPER_LAB_LIVE_INTAKE_OPT_IN=true in .env to enable"
            }>
              {liveEnabled ? "Run live arXiv intake" : "Live arXiv disabled (opt-in)"}
            </button>
          </form>
        </div>
      </section>

      <section className="card">
        <h2>Download open PDFs</h2>
        <p className="muted">
          Iterates over all <span className="code">accepted</span> papers with a
          known <span className="code">pdfUrl</span> and downloads them into{" "}
          <span className="code">data/pdfs/</span>. Live network is opt-in
          via <span className="code">PAPER_LAB_DOWNLOAD_LIVE_OPT_IN</span>.
        </p>
        <form action={runDownloadAllAction}>
          <button
            type="submit"
            disabled={!downloadLiveEnabled}
            title={
              downloadLiveEnabled
                ? "Attempt to download open PDFs for all accepted papers"
                : "Set PAPER_LAB_DOWNLOAD_LIVE_OPT_IN=true in .env to enable"
            }
          >
            {downloadLiveEnabled
              ? "Download PDFs for accepted papers"
              : "Download disabled (opt-in)"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Local model</h2>
        <p className="muted">
          Active provider: <span className="code">{modelProvider}</span> — {modelSummary}.
        </p>
        {showModelHealthButton ? (
          <form action={runModelHealthAction}>
            <button type="submit" className="primary">Check local model health</button>
          </form>
        ) : (
          <p className="muted">
            The health probe is only available when the provider is{" "}
            <span className="code">ollama</span> AND{" "}
            <span className="code">PAPER_LAB_LIVE_MODEL_OPT_IN=true</span> is set.
          </p>
        )}
      </section>

      <section className="card">
        <h2>Recent intake runs</h2>
        {runs.length === 0 ? (
          <p className="empty">No runs yet. Trigger one above.</p>
        ) : (
          <table className="run-table">
            <thead>
              <tr>
                <th>id</th>
                <th>source</th>
                <th>mode</th>
                <th>query</th>
                <th>accepted</th>
                <th>rejected</th>
                <th>finished</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id}>
                  <td className="code">{r.id}</td>
                  <td>{r.source}</td>
                  <td>
                    {isFixtureSource(r.source) ? (
                      <span className="badge warn">fixture</span>
                    ) : (
                      <span className="badge good">live</span>
                    )}
                  </td>
                  <td className="code">{r.query}</td>
                  <td>{r.acceptedCount}</td>
                  <td>{r.rejectedCount}</td>
                  <td className="muted">{r.finishedAt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
