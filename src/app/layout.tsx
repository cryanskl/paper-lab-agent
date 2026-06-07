import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "paper-lab-agent",
  description:
    "Local-first research assistant: paper intake, bilingual reading, RAG Q&A, simulation specs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="site-header">
          <div className="brand">
            <Link href="/">paper-lab-agent</Link>
            <span className="tagline">local-first V1</span>
          </div>
          <nav className="site-nav">
            <Link href="/library">Library</Link>
            <Link href="/ask">Ask Papers</Link>
            <Link href="/simulation">Simulation</Link>
            <Link href="/sources">Sources</Link>
          </nav>
        </header>
        <main className="site-main">{children}</main>
        <footer className="site-footer">
          V1 harness mode · deterministic fake model · fixture-backed data
        </footer>
      </body>
    </html>
  );
}
