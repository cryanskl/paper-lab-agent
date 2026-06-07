// Domain types for paper-lab-agent V1.
// All persistent records are described here. The fake model adapter
// only returns values matching these shapes; tests assert against them.

export type IntakeDecision = "accepted" | "rejected";
export type DownloadStatus = "not_attempted" | "succeeded" | "download_failed";

export interface Paper {
  paperId: string;
  externalId: string | null;
  source: string;
  title: string;
  authors: string[];
  abstract: string;
  sourceUrl: string;
  pdfUrl: string | null;
  pdfPath: string | null;
  publishedAt: string | null;
  status: IntakeDecision;
  relevanceRationale: string;
  downloadStatus: DownloadStatus;
  downloadError: string | null;
  keywords: string[];
  importedAt: string;
}

export interface PaperSegment {
  paperId: string;
  segmentId: string;
  order: number;
  page: number | null;
  english: string;
  chinese: string;
}

export interface IntakeRun {
  id: number;
  source: string;
  query: string;
  startedAt: string;
  finishedAt: string;
  candidateCount: number;
  acceptedCount: number;
  rejectedCount: number;
  downloadFailureCount: number;
  errorLog: string;
}

export interface Citation {
  paperId: string;
  segmentId: string;
  paperTitle: string;
}

export interface AssistantAnswer {
  question: string;
  retrievedSegments: PaperSegment[];
  answer: string;
  citations: Citation[];
  insufficientEvidence: boolean;
}

export interface SimulationSpec {
  sourceEvidence: string;
  assumptions: string[];
  parameters: Array<{ name: string; value: number; unit: string; description: string }>;
  units: string[];
  boundaryConditions: string[];
  runSteps: string[];
  artifactPaths: string[];
}

export interface RelevanceInput {
  title: string;
  abstract: string;
  keywords: string[];
  profileKeywords: string[];
}

export interface RelevanceResult {
  decision: IntakeDecision;
  rationale: string;
  matchedKeywords: string[];
}
