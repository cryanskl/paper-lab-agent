import { describe, it, expect } from "vitest";
import fs from "node:fs";
import path from "node:path";
import { resolveFixturePath } from "./helpers/setup";
import {
  parseArxivAtom,
  fetchArxivCandidates,
  ArxivAccessError,
  ARXIV_API_ENDPOINT,
} from "@/lib/intake/arxiv-client";

const FIXTURE_XML = path.resolve(
  process.cwd(),
  "fixtures/intake/arxiv-live-sample.xml",
);

describe("arxiv metadata normalization (no network)", () => {
  it("parses the recorded arXiv fixture into stable candidate records", () => {
    const xml = fs.readFileSync(FIXTURE_XML, "utf-8");
    const candidates = parseArxivAtom(xml);
    expect(candidates).toHaveLength(2);

    const first = candidates[0];
    // Version suffix must be stripped from the arxiv id.
    expect(first.arxivId).toBe("2606.00001");
    expect(first.title).toBe(
      "Physics-Informed Surrogate Models for Engineering Simulation",
    );
    expect(first.authors).toEqual(["A. Researcher", "B. Coauthor"]);
    expect(first.abstract).toContain("physics-informed");
    expect(first.publishedAt).toBe("2026-06-01T00:00:00Z");
    expect(first.sourceUrl).toBe("https://arxiv.org/abs/2606.00001");
    expect(first.pdfUrl).toBe("http://arxiv.org/pdf/2606.00001v1");
    expect(first.rawKeywords).toEqual(
      expect.arrayContaining(["cs.AI", "physics.comp-ph"]),
    );
  });

  it("marks the unrelated entry as keyword-light", () => {
    const xml = fs.readFileSync(FIXTURE_XML, "utf-8");
    const candidates = parseArxivAtom(xml);
    const second = candidates[1];
    expect(second.arxivId).toBe("2606.00002");
    expect(second.title).toContain("Social Media");
    expect(second.authors).toEqual(["C. Sociologist"]);
    // The unrelated entry has no engineering / physics keywords.
    expect(
      second.rawKeywords.some((k) => /physics|engineering|surrogate/i.test(k)),
    ).toBe(false);
  });

  it("decodes common HTML entities in titles and summaries", () => {
    const xml = `
      <feed xmlns="http://www.w3.org/2005/Atom">
        <entry>
          <id>http://arxiv.org/abs/2606.99999v1</id>
          <published>2026-06-07T00:00:00Z</published>
          <title>AT&amp;T &quot;Smart&quot; Agents &amp; ML</title>
          <summary>Agents &amp; ML for &quot;smart&quot; flow control.</summary>
          <author><name>D. Engineer</name></author>
          <link title="pdf" href="http://arxiv.org/pdf/2606.99999v1" rel="related" type="application/pdf"/>
          <category term="cs.AI"/>
        </entry>
      </feed>
    `;
    const [c] = parseArxivAtom(xml);
    expect(c.title).toBe('AT&T "Smart" Agents & ML');
    expect(c.abstract).toBe('Agents & ML for "smart" flow control.');
  });

  it("rejects empty input", () => {
    expect(() => parseArxivAtom("")).toThrow(ArxivAccessError);
  });
});

describe("arxiv client network gate", () => {
  it("refuses to fetch when allowNetwork is false (the default mode)", async () => {
    await expect(
      fetchArxivCandidates("cat:cs.AI", { allowNetwork: false }),
    ).rejects.toThrow(/network disabled/);
  });

  it("refuses an empty query even when network is allowed", async () => {
    const stubFetch = (() => {
      throw new Error("fetch should not be called for empty query");
    }) as unknown as typeof fetch;
    await expect(
      fetchArxivCandidates("", { allowNetwork: true, fetchImpl: stubFetch }),
    ).rejects.toThrow(/empty/);
  });

  it("uses the provided endpoint and surfaces non-2xx responses", async () => {
    const calls: string[] = [];
    const stubFetch = (async (url: string) => {
      calls.push(url);
      return new Response("upstream error", { status: 503, statusText: "Service Unavailable" });
    }) as unknown as typeof fetch;
    await expect(
      fetchArxivCandidates("cat:cs.AI", {
        allowNetwork: true,
        fetchImpl: stubFetch,
        endpoint: "https://example.test/arxiv",
      }),
    ).rejects.toThrow(/503/);
    expect(calls).toHaveLength(1);
    expect(calls[0]).toBe(
      "https://example.test/arxiv?search_query=cat%3Acs.AI&start=0&max_results=10",
    );
  });

  it("default endpoint is export.arxiv.org", () => {
    expect(ARXIV_API_ENDPOINT).toBe("https://export.arxiv.org/api/query");
  });

  it("respects resolveFixturePath for the recorded XML path", () => {
    // Sanity check that the helper resolves where the file actually lives.
    const resolved = resolveFixturePath("fixtures/intake/arxiv-live-sample.xml");
    expect(fs.existsSync(resolved)).toBe(true);
  });
});
