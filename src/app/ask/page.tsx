import Link from "next/link";
import { askQuestion } from "@/lib/assistant/answer";
import { loadConfig } from "@/lib/config";
import fs from "node:fs";

export const dynamic = "force-dynamic";

interface GoldenQuestion {
  id: string;
  question: string;
}

function loadGoldenQuestions(): GoldenQuestion[] {
  const cfg = loadConfig();
  if (!fs.existsSync(cfg.fixtures.goldenQa)) return [];
  const data = JSON.parse(fs.readFileSync(cfg.fixtures.goldenQa, "utf-8")) as {
    questions: GoldenQuestion[];
  };
  return data.questions;
}

export default function AskPage({
  searchParams,
}: {
  searchParams: { q?: string };
}) {
  const question = (searchParams.q ?? "").trim();
  const goldenQuestions = loadGoldenQuestions();

  let answer: ReturnType<typeof askQuestion> | null = null;
  let askError: string | null = null;
  if (question.length > 0) {
    try {
      answer = askQuestion(question);
    } catch (err) {
      askError = err instanceof Error ? err.message : String(err);
    }
  }

  return (
    <div>
      <h1>Ask Papers</h1>
      <p className="muted">
        RAG Q&amp;A across all ingested paper segments. Answers must include paper
        and segment citations; unsupported questions return{" "}
        <span className="code">insufficient evidence</span>.
      </p>

      <form className="ask-form" method="get" action="/ask">
        <input
          type="text"
          name="q"
          defaultValue={question}
          placeholder="Ask a question about the ingested papers…"
          aria-label="Question"
        />
        <button type="submit">Ask</button>
      </form>

      {askError ? (
        <div className="warn-box">{askError}</div>
      ) : answer ? (
        <div className="card">
          <h2>Question</h2>
          <p>{answer.question}</p>
          <h2>Answer</h2>
          {answer.insufficientEvidence ? (
            <p className="badge bad">insufficient evidence</p>
          ) : (
            <p>{answer.answer}</p>
          )}
          <h3>Citations</h3>
          {answer.citations.length === 0 ? (
            <p className="muted">No citations — answer is unverified.</p>
          ) : (
            <p>
              {answer.citations.map((c) => (
                <span className="citation" key={`${c.paperId}::${c.segmentId}`}>
                  {c.paperId} · {c.segmentId}
                </span>
              ))}
            </p>
          )}
          {answer.retrievedSegments.length > 0 && (
            <details>
              <summary>Retrieved segments ({answer.retrievedSegments.length})</summary>
              <ul className="spec-list">
                {answer.retrievedSegments.map((s) => (
                  <li key={s.segmentId}>
                    <span className="code">{s.segmentId}</span> — {s.english}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </div>
      ) : null}

      <h2>Golden questions (from fixture)</h2>
      <p className="muted">Click to run each question through the RAG harness.</p>
      <ul className="spec-list">
        {goldenQuestions.map((g) => (
          <li key={g.id}>
            <span className="code">{g.id}</span> ·{" "}
            <Link href={`/ask?q=${encodeURIComponent(g.question)}`}>{g.question}</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
