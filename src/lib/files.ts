// Local data-directory layout. V1 uses this as the convention for
// PDFs / parsed text / translations / simulation outputs.

import fs from "node:fs";
import path from "node:path";
import { loadConfig } from "./config";

export interface DataLayout {
  dataDir: string;
  pdfDir: string;
  textDir: string;
  translationDir: string;
  simulationDir: string;
}

export function getDataLayout(): DataLayout {
  const cfg = loadConfig();
  return {
    dataDir: cfg.dataDir,
    pdfDir: cfg.pdfDir,
    textDir: cfg.textDir,
    translationDir: cfg.translationDir,
    simulationDir: cfg.simulationDir,
  };
}

export function ensureDataDirs(): DataLayout {
  const layout = getDataLayout();
  for (const dir of [
    layout.dataDir,
    layout.pdfDir,
    layout.textDir,
    layout.translationDir,
    layout.simulationDir,
  ]) {
    fs.mkdirSync(dir, { recursive: true });
  }
  return layout;
}

export function translationPath(paperId: string, segmentId: string): string {
  const layout = getDataLayout();
  return path.join(layout.translationDir, paperId, `${segmentId}.json`);
}
