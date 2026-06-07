// One-shot fixture importer. Run with `pnpm seed` (which uses
// `node --env-file=.env --import tsx ...`). Runs the intake +
// segment import + writes a simulation artifact. Idempotent:
// re-running upserts papers and replaces segments by id.

import { loadConfig } from "../src/lib/config";
import { ensureDataDirs } from "../src/lib/files";
import { getDb } from "../src/lib/db";
import { importIntakeFixture, listIntakeRuns } from "../src/lib/intake/import-fixture";
import { importSegmentsFixture, getAllSegments } from "../src/lib/library/segments";
import { listPapers } from "../src/lib/library/papers";
import { buildSimulationSpec, loadMethodFixture, writeSimulationArtifact } from "../src/lib/simulation/build-spec";

function main(): void {
  ensureDataDirs();
  // Force DB initialization so the schema exists even if no intake rows land.
  getDb();

  const cfg = loadConfig();

  console.log(`[seed] data dir: ${cfg.dataDir}`);
  console.log(`[seed] db url:   ${cfg.databaseUrl}`);

  console.log(`[seed] importing intake fixture: ${cfg.fixtures.intake}`);
  const intake = importIntakeFixture(cfg.fixtures.intake);
  console.log(
    `[seed] intake run #${intake.run.id}: ${intake.run.candidateCount} candidates, ${intake.run.acceptedCount} accepted, ${intake.run.rejectedCount} rejected`,
  );

  console.log(`[seed] importing segment fixture: ${cfg.fixtures.segments}`);
  const segs = importSegmentsFixture(cfg.fixtures.segments);
  console.log(
    `[seed] segments imported for ${segs.paperIds.length} paper(s): ${JSON.stringify(segs.segmentCounts)}`,
  );

  console.log(`[seed] generating simulation spec from: ${cfg.fixtures.simulationMethod}`);
  const methodText = loadMethodFixture(cfg.fixtures.simulationMethod);
  const firstAccepted = listPapers().find((p) => p.status === "accepted");
  const spec = buildSimulationSpec(methodText, firstAccepted?.paperId ?? null);
  const artifactPath = writeSimulationArtifact(spec, firstAccepted?.paperId ?? null);
  console.log(`[seed] simulation spec written to: ${artifactPath}`);

  console.log(`[seed] done. intake runs in DB: ${listIntakeRuns().length}`);
  console.log(`[seed] total segments in DB: ${getAllSegments().length}`);
}

main();
