import { describe, it, expect, beforeAll, afterAll, beforeEach } from "vitest";
import {
  setupTempDataDir,
  teardownTempDataDir,
} from "./helpers/setup";
import {
  getModelAdapter,
  resetModelAdapterForTesting,
  isOllamaOptIn,
} from "@/lib/models";
import { OllamaAdapter, OllamaUnavailableError } from "@/lib/models/ollama-adapter";
import { checkProviderHealth } from "@/lib/models/health";
import type { PaperSegment } from "@/types/domain";

describe("fake adapter remains the default in V1", () => {
  beforeAll(() => {
    setupTempDataDir();
  });
  afterAll(() => {
    teardownTempDataDir();
  });

  beforeEach(() => {
    // Each test must start with a fresh, un-cached adapter factory
    // because previous tests may have replaced the cached one.
    resetModelAdapterForTesting(null);
  });

  it("returns the fake adapter by default", () => {
    const adapter = getModelAdapter();
    expect(adapter.name).toBe("fake");
  });

  it("refuses ollama when the live opt-in flag is off", () => {
    process.env.PAPER_LAB_MODEL_PROVIDER = "ollama";
    // PAPER_LAB_LIVE_MODEL_OPT_IN stays unset
    expect(() => getModelAdapter()).toThrow(/PAPER_LAB_LIVE_MODEL_OPT_IN/);
  });

  it("constructs an OllamaAdapter when both provider and opt-in are set", () => {
    process.env.PAPER_LAB_MODEL_PROVIDER = "ollama";
    process.env.PAPER_LAB_LIVE_MODEL_OPT_IN = "true";
    process.env.PAPER_LAB_OLLAMA_URL = "http://example.test:11434";
    process.env.PAPER_LAB_OLLAMA_MODEL = "llama3";
    const adapter = getModelAdapter();
    expect(adapter).toBeInstanceOf(OllamaAdapter);
    expect(adapter.name).toBe("ollama");
  });

  it("rejects an unknown provider name", () => {
    process.env.PAPER_LAB_MODEL_PROVIDER = "openai";
    expect(() => getModelAdapter()).toThrow(/Unknown PAPER_LAB_MODEL_PROVIDER/);
  });

  it("isOllamaOptIn only accepts the literal 'true'", () => {
    expect(isOllamaOptIn("true")).toBe(true);
    expect(isOllamaOptIn("TRUE")).toBe(false);
    expect(isOllamaOptIn("1")).toBe(false);
    expect(isOllamaOptIn(undefined)).toBe(false);
  });
});

describe("OllamaAdapter with stubbed fetch (no real network)", () => {
  const fakeFetch = (response: unknown, status = 200) =>
    (async () =>
      new Response(JSON.stringify(response), {
        status,
        headers: { "content-type": "application/json" },
      })) as unknown as typeof fetch;

  it("translate forwards the english text and returns the response field", async () => {
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch({ response: "你好" }),
    });
    const out = await adapter.translate("hello");
    expect(out).toBe("你好");
  });

  it("translate returns an empty string for an empty input without calling fetch", async () => {
    let called = 0;
    const stub = (async () => {
      called += 1;
      return new Response(JSON.stringify({ response: "x" }), { status: 200 });
    }) as unknown as typeof fetch;
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: stub,
    });
    expect(await adapter.translate("")).toBe("");
    expect(called).toBe(0);
  });

  it("scoreRelevance marks the paper accepted when the model says ACCEPT", async () => {
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch({ response: "ACCEPT — matches neural surrogate" }),
    });
    const r = await adapter.scoreRelevance({
      title: "Neural surrogate",
      abstract: "abstract",
      keywords: [],
      profileKeywords: ["neural surrogate"],
    });
    expect(r.decision).toBe("accepted");
  });

  it("scoreRelevance marks the paper rejected when the model says REJECT", async () => {
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch({ response: "REJECT — unrelated domain" }),
    });
    const r = await adapter.scoreRelevance({
      title: "Pasta cooking times",
      abstract: "abstract",
      keywords: [],
      profileKeywords: ["neural surrogate"],
    });
    expect(r.decision).toBe("rejected");
  });

  it("generateAnswer returns insufficient evidence for empty retrieval", async () => {
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch({ response: "should not be called" }),
    });
    const out = await adapter.generateAnswer("q", [], {});
    expect(out.insufficientEvidence).toBe(true);
    expect(out.citations).toEqual([]);
  });

  it("generateAnswer builds citations for every retrieved segment", async () => {
    const segs: PaperSegment[] = [
      { paperId: "p1", segmentId: "p1-s1", order: 0, page: null, english: "alpha", chinese: "" },
      { paperId: "p1", segmentId: "p1-s2", order: 1, page: null, english: "beta", chinese: "" },
    ];
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch({ response: "Source: p1 / p1-s1" }),
    });
    const out = await adapter.generateAnswer("q", segs, { p1: "Title" });
    expect(out.citations).toHaveLength(2);
    expect(out.citations[0].paperTitle).toBe("Title");
    expect(out.insufficientEvidence).toBe(false);
  });

  it("surfaces a typed error when the model returns non-2xx", async () => {
    const adapter = new OllamaAdapter({
      endpoint: "http://example.test:11434",
      model: "llama3",
      fetchImpl: fakeFetch("model not found", 404),
    });
    await expect(adapter.translate("hi")).rejects.toBeInstanceOf(OllamaUnavailableError);
  });
});

describe("checkProviderHealth with stubbed fetch", () => {
  it("returns ok for the fake provider without making any network call", async () => {
    const r = await checkProviderHealth({ provider: "fake" });
    expect(r.ok).toBe(true);
    expect(r.model).toBe("fake");
  });

  it("returns ok for ollama when /api/tags responds with at least one model", async () => {
    const stub = (async () =>
      new Response(JSON.stringify({ models: [{ name: "llama3" }] }), {
        status: 200,
        headers: { "content-type": "application/json" },
      })) as unknown as typeof fetch;
    const r = await checkProviderHealth({
      provider: "ollama",
      endpoint: "http://example.test:11434",
      fetchImpl: stub,
    });
    expect(r.ok).toBe(true);
    expect(r.model).toBe("llama3");
  });

  it("returns a clear error when ollama responds with 503", async () => {
    const stub = (async () =>
      new Response("upstream error", { status: 503, statusText: "Service Unavailable" })) as unknown as typeof fetch;
    const r = await checkProviderHealth({
      provider: "ollama",
      endpoint: "http://example.test:11434",
      fetchImpl: stub,
    });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/503/);
  });

  it("returns a clear error when the fetch itself throws (connection refused)", async () => {
    const stub = (async () => {
      throw new Error("ECONNREFUSED");
    }) as unknown as typeof fetch;
    const r = await checkProviderHealth({
      provider: "ollama",
      endpoint: "http://example.test:11434",
      fetchImpl: stub,
    });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/not reachable/);
  });

  it("rejects an unknown provider explicitly", async () => {
    const r = await checkProviderHealth({ provider: "openai" });
    expect(r.ok).toBe(false);
    expect(r.message).toMatch(/unknown provider/i);
  });
});
