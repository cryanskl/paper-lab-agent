// arXiv metadata intake client.
//
// Phase 2 only fetches metadata (Atom XML from export.arxiv.org/api/query).
// We never download PDFs through this module — PDF acquisition is the
// Phase 3 responsibility and uses the same source-and-download policy.
//
// Network access is **explicitly opt-in** via `allowNetwork: true`. The
// default mode in this repo is fixture-only, so callers that forget to
// opt in fail loudly instead of silently hitting the network.

export interface ArxivCandidate {
  /** arXiv id, e.g. "2606.00001v1" or "2606.00001". */
  arxivId: string;
  /** Human title. */
  title: string;
  authors: string[];
  abstract: string;
  /** Public arXiv abstract page URL. */
  sourceUrl: string;
  /** Direct PDF URL on arxiv.org (we never fetch it from Phase 2). */
  pdfUrl: string;
  publishedAt: string | null;
  rawKeywords: string[];
}

export interface FetchArxivOptions {
  allowNetwork: boolean;
  maxResults?: number;
  /** Override fetch for tests; defaults to globalThis.fetch. */
  fetchImpl?: typeof fetch;
  /** Override the API endpoint, mainly for test fixtures. */
  endpoint?: string;
}

export class ArxivAccessError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ArxivAccessError";
  }
}

export const ARXIV_API_ENDPOINT = "https://export.arxiv.org/api/query";

function decodeEntities(input: string): string {
  // arXiv sometimes returns HTML-entity-escaped text inside <title> and
  // <summary>. We do a minimal unescape that covers the common cases.
  return input
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

function stripArxivIdVersion(id: string): string {
  // arXiv ids look like "http://arxiv.org/abs/2606.00001v1" — we want
  // the bare id without the URL prefix or version suffix for stable
  // paper ids.
  const noScheme = id.replace(/^https?:\/\//, "");
  const tail = noScheme.includes("/") ? noScheme.split("/").pop() ?? noScheme : noScheme;
  return tail.replace(/v\d+$/, "");
}

function textOf(re: RegExp, source: string): string {
  const m = source.match(re);
  return m ? m[1].trim() : "";
}

export function parseArxivAtom(xml: string): ArxivCandidate[] {
  if (typeof xml !== "string" || xml.trim() === "") {
    throw new ArxivAccessError("parseArxivAtom: empty input");
  }
  const entries = xml.split(/<entry>/i).slice(1);
  const out: ArxivCandidate[] = [];
  for (const entry of entries) {
    const slice = entry.split(/<\/entry>/i)[0];

    const idRaw = textOf(/<id>\s*([^<]+?)\s*<\/id>/i, slice);
    if (!idRaw) continue;
    const arxivId = stripArxivIdVersion(decodeEntities(idRaw));

    const title = decodeEntities(textOf(/<title>\s*([^<]+?)\s*<\/title>/i, slice))
      .replace(/\s+/g, " ")
      .trim();
    if (!title) continue;

    const summaryRaw = textOf(/<summary>\s*([\s\S]*?)\s*<\/summary>/i, slice);
    const abstract = decodeEntities(summaryRaw).replace(/\s+/g, " ").trim();

    const publishedAtRaw = textOf(/<published>\s*([^<]+?)\s*<\/published>/i, slice);
    const publishedAt = publishedAtRaw || null;

    const authorBlocks = slice.match(/<author>\s*<name>([\s\S]*?)<\/name>\s*<\/author>/gi) ?? [];
    const authors = authorBlocks
      .map((b) => {
        const m = b.match(/<name>([\s\S]*?)<\/name>/i);
        return m ? decodeEntities(m[1]).trim() : "";
      })
      .filter(Boolean);

    // arXiv exposes the PDF link as <link rel="related" type="application/pdf" href="..."/>.
    // Attribute order varies, so we grab all <link ...> tags and inspect
    // each one instead of relying on a single fixed-order regex.
    const linkTags = slice.match(/<link[^>]*\/>/gi) ?? [];
    let pdfLink = "";
    for (const tag of linkTags) {
      const href = textOf(/href="([^"]+)"/i, tag);
      const rel = textOf(/rel="([^"]+)"/i, tag);
      const type = textOf(/type="([^"]+)"/i, tag);
      if (!href) continue;
      const looksLikePdf =
        rel === "related" || /\.pdf(\?|#|$)/i.test(href) || type === "application/pdf";
      if (looksLikePdf) {
        pdfLink = href;
        break;
      }
    }
    const pdfUrl = pdfLink || `https://arxiv.org/pdf/${arxivId}.pdf`;

    const sourceUrl = `https://arxiv.org/abs/${arxivId}`;

    // Use arXiv categories as a low-effort keyword hint. The real
    // relevance decision still goes through the ModelAdapter.
    const catMatches = slice.match(/<category[^>]*term="([^"]+)"/gi) ?? [];
    const rawKeywords = catMatches
      .map((c) => {
        const m = c.match(/term="([^"]+)"/);
        return m ? m[1] : "";
      })
      .filter(Boolean);

    out.push({
      arxivId,
      title,
      authors,
      abstract,
      sourceUrl,
      pdfUrl,
      publishedAt,
      rawKeywords,
    });
  }
  return out;
}

export async function fetchArxivCandidates(
  query: string,
  options: FetchArxivOptions,
): Promise<ArxivCandidate[]> {
  if (!options.allowNetwork) {
    throw new ArxivAccessError(
      "network disabled in current mode; pass allowNetwork: true to opt in",
    );
  }
  if (!query || query.trim() === "") {
    throw new ArxivAccessError("fetchArxivCandidates: query is empty");
  }
  const maxResults = Math.max(1, Math.min(options.maxResults ?? 10, 50));
  const endpoint = options.endpoint ?? ARXIV_API_ENDPOINT;
  const url = `${endpoint}?search_query=${encodeURIComponent(query)}&start=0&max_results=${maxResults}`;
  const fetchImpl = options.fetchImpl ?? globalThis.fetch;
  if (typeof fetchImpl !== "function") {
    throw new ArxivAccessError("global fetch is not available in this runtime");
  }
  const res = await fetchImpl(url, {
    headers: { "user-agent": "paper-lab-agent/0.1 (local research assistant)" },
  });
  if (!res.ok) {
    throw new ArxivAccessError(`arxiv api responded ${res.status} ${res.statusText}`);
  }
  const xml = await res.text();
  return parseArxivAtom(xml);
}
